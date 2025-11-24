#include <stdlib.h> 
#include <WiFi.h>      // For Wi-Fi Connectivity
#include <PubSubClient.h> // For MQTT Protocol

// ------------------------------------
// 1. CONFIGURATION (*** CRITICAL: UPDATE THESE VALUES ***)
// ------------------------------------
const char* ssid = "Hyperoptic Fibre 7323";            
const char* password = "UjrjR7Y4C437U4";      

// FIX THIS: Replace with the ACTUAL IP address of your Raspberry Pi (Mosquitto Broker)
const char* mqtt_server = "192.168.1.108";    

const char* mqtt_client_id = "ESP32_HMMD_MQTT_01"; 
const char* mqtt_publish_topic = "home/bedroom/presence"; 

// --- SAMPLING RATE FOR AI TRAINING (10Hz) ---
// We only publish to MQTT if 100ms has passed since the last successful decode.
const long TARGET_SAMPLE_RATE_MS = 100; 
long last_sample_time = 0; // Tracks when the last publish occurred

// --- SERIAL PINS (UART1) ---
#define RX1_PIN 18 // HMMD TX connects to ESP32 RX (Input)
#define TX1_PIN 19 // HMMD RX connects to ESP32 TX (Output)
#define HMMD_BAUDRATE 115200 

// --- HMMD Command Data ---
// Configuration command to ensure the sensor is streaming data
String hex_to_send = "FDFCFBFA0800120000006400000004030201"; 

// Constants for Packet Decoding
const byte HEADER_1 = 0xFD; 
const byte HEADER_2 = 0xFC; 
const int PACKET_LENGTH = 14; 
const int DISTANCE_OFFSET = 8; // Assumed offset of the distance field (Must be verified with datasheet!)
const int DISTANCE_FIELD_LENGTH = 2; 

// ------------------------------------
// 2. GLOBALS & OBJECTS
// ------------------------------------
HardwareSerial HMMDSerial(1); // Custom serial object for sensor communication (UART1)
WiFiClient espClient;         
PubSubClient client(espClient); 


// --- Function Prototypes ---
void sendHexData(String hexString);
void readAndProcessSensorLines();
void setup_wifi();
void reconnect();


// ------------------------------------
// 3. WIFI SETUP 
// ------------------------------------
void setup_wifi() {
    delay(10);
    Serial.print("Connecting to ");
    Serial.println(ssid);
    
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}


// ------------------------------------
// 4. MQTT RECONNECTION LOGIC
// ------------------------------------
void reconnect() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        
        if (client.connect(mqtt_client_id)) {
            Serial.println("connected to broker!");
            client.publish("home/status", "ESP32 HMMD Sensor Online");
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" trying again in 5 seconds");
            delay(5000);
        }
    }
}


// ------------------------------------
// 5. COMMAND SENDER
// ------------------------------------
void sendHexData(String hexString) {
    int hexStringLength = hexString.length();
    if (hexStringLength % 2 != 0) return;
 
    int byteCount = hexStringLength / 2;
    byte hexBytes[byteCount];
    for (int i = 0; i < hexStringLength; i += 2) {
        String byteString = hexString.substring(i, i + 2);
        byte hexByte = (byte)strtoul(byteString.c_str(), NULL, 16);
        hexBytes[i / 2] = hexByte;
    }
    
    Serial.print("TX: ");
    for(int i=0; i<byteCount; i++) {
        if (hexBytes[i] < 16) Serial.print("0");
        Serial.print(hexBytes[i], HEX);
        Serial.print(" ");
    }
    Serial.println();
    
    HMMDSerial.write(hexBytes, byteCount); // Send data via HMMDSerial (UART1)
}


// ------------------------------------
// 6. DECODING & PUBLISHING LOGIC (WITH SAMPLING CONTROL)
// ------------------------------------
void decodeAndPublishDistance(byte header1, byte header2) {
    byte buffer[PACKET_LENGTH];
    
    // Check if the rest of the packet is available
    if (HMMDSerial.available() >= (PACKET_LENGTH - 2)) {
        
        // Read the rest of the available packet
        // Start buffer from index 2, as 0 and 1 are the headers
        HMMDSerial.readBytes(&buffer[2], PACKET_LENGTH - 2); 

        // 1. EXTRACT DISTANCE BYTES (Assumed Little Endian)
        // Check if distance offset is within the buffer bounds
        if (DISTANCE_OFFSET + DISTANCE_FIELD_LENGTH > PACKET_LENGTH) {
            Serial.println("Error: Distance offset out of bounds.");
            // Read remaining data to clear buffer
            while(HMMDSerial.available()) HMMDSerial.read();
            return;
        }

        uint16_t rawDistance = (buffer[DISTANCE_OFFSET + 1] << 8) | buffer[DISTANCE_OFFSET];
        
        // 2. CONVERT TO CENTIMETERS (Assumed scaling factor)
        float distance_cm = (float)rawDistance / 10.0; 
        
        // --- MQTT PUBLISHING ---
        if (client.connected()) {
            // Convert float distance to a character array for MQTT payload
            char payload[10];
            dtostrf(distance_cm, 5, 2, payload); // Convert float to string
            
            // Publish the distance to the MQTT broker
            client.publish(mqtt_publish_topic, payload);
            
            Serial.print("MQTT Pub (10Hz): ");
            Serial.print(payload);
            Serial.println(" cm");
        }
        
    } else {
        // Not enough data for a full packet; discard to sync for the next full packet.
        while(HMMDSerial.available()) HMMDSerial.read();
    }
}

void readAndProcessSensorLines() {
    // 1. CHECK SAMPLING RATE: Drop the packet if TARGET_SAMPLE_RATE_MS has not passed.
    if (millis() - last_sample_time < TARGET_SAMPLE_RATE_MS) {
        // Discard data to clear the buffer if we are too fast
        while (HMMDSerial.available()) HMMDSerial.read(); 
        return; 
    }
    
    // 2. ONLY PROCEED IF NEW DATA IS AVAILABLE AFTER TIMEOUT
    if (HMMDSerial.available() > 0) {
        
        // --- STEP A: Look for the Start Header (FD FC) ---
        byte header1 = HMMDSerial.read();

        if (header1 == HEADER_1) {
            
            if (HMMDSerial.available() > 0) {
                byte header2 = HMMDSerial.read();
                
                if (header2 == HEADER_2) {
                    
                    last_sample_time = millis(); // RESET THE SAMPLING TIMER ONLY ON SUCCESSFUL HEADER DECODE
                    
                    // --- STEP B: Decode and Publish ---
                    decodeAndPublishDistance(header1, header2);
                    
                }
            }
        }
    }
}


// ------------------------------------
// 7. SETUP & LOOP (Main Program Flow)
// ------------------------------------
void setup() {
    Serial.begin(115200); 
    
    unsigned long startAttemptTime = millis();
    while (!Serial && millis() - startAttemptTime < 2000) {
        delay(100);
    }
    Serial.println("Serial Monitor Initialized.");
    
    // Initialize Wi-Fi and connect to the network
    setup_wifi(); 
    client.setServer(mqtt_server, 1883); // Set MQTT server details
    
    // Start the sensor serial port (UART1)
    HMMDSerial.begin(HMMD_BAUDRATE, SERIAL_8N1, RX1_PIN, TX1_PIN);
    Serial.println("Serial1 Initialized on RX:" + String(RX1_PIN) + ", TX:" + String(TX1_PIN));
    
    Serial.println("Sending Configuration Hex Command...");
    sendHexData(hex_to_send);
    Serial.println("Initial command sent.");
    
    Serial.println("Waiting 5 seconds for sensor to initialize and stream data...");
    delay(5000); 
    Serial.println("Start Monitoring Sensor Stream (10Hz Target).");
    
    // Set the initial sample time here to ensure the first packet is sent immediately
    last_sample_time = millis();
}
    
void loop() {
    // 1. Maintain MQTT Connection (Must be called frequently)
    if (!client.connected()) {
        reconnect();
    }
    client.loop(); 

    // 2. Read and Publish Sensor Data (Now controlled by TARGET_SAMPLE_RATE_MS)
    readAndProcessSensorLines();
    
    delay(1); // Minimal delay to keep loop running fast
}