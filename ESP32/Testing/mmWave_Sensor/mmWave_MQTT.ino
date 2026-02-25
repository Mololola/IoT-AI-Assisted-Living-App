#include <stdlib.h> 
#include <WiFi.h>      // For Wi-Fi Connectivity
#include <PubSubClient.h> // For MQTT Protocol


// 1. CONFIGURATION 

const char* ssid = "IoT-Lab";            // Your WiFi Network Name
const char* password = "ELEC423_2526!";      // Your WiFi Password
const char* mqtt_server = "192.168.1.100";   

const char* mqtt_client_id = "ESP32_HMMD_MQTT_01"; 
const char* mqtt_publish_topic = "home/bedroom/presence"; 

// --- PUBLISH INTERVAL (2 seconds) ---
const long TARGET_PUBLISH_INTERVAL_MS = 500; 
long lastReadTime = 0; // Tracks when the last publish occurred

// --- HMMD SERIAL PINS ---
#define RX1_PIN 18
#define TX1_PIN 19
#define HMMD_BAUDRATE 115200 

// HMMD command (Configuration command to ensure the sensor is streaming data)
// *** KEEPING this for initialization, but the parser relies on text output. ***
String hex_to_send = "FDFCFBFA0800120000006400000004030201"; 

// Constants for Packet Decoding (These are now only placeholders, as we use line reading)
const int PACKET_LENGTH = 14; 
const int DISTANCE_OFFSET = 8; 
const int DISTANCE_FIELD_LENGTH = 2; 

// Globals and Objects 
HardwareSerial HMMDSerial(1); // Custom serial object for sensor communication
WiFiClient espClient;         
PubSubClient client(espClient); 


// Functions 
void sendHexData(String hexString);
void readAndPublishData();
void setup_wifi();
void reconnect();

//WiFi and MQTT Setup 
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


//Comamand Sendor 
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

// Timed readings and Logic 

void readAndPublishData() {
   
    // Read any available data from the sensor port (HMMDSerial)
    if (HMMDSerial.available() > 0) {
        
        // Read until a newline is found (assuming sensor sends text lines)
        String line = HMMDSerial.readStringUntil('\n');
        line.trim();

        // We are looking for the 'Range' value, which should be dynamic.
        if (line.startsWith("Range ")) {
            
    
            if (millis() - lastReadTime < TARGET_PUBLISH_INTERVAL_MS) {
                return; // Too soon, discard the reading and exit
            }
            lastReadTime = millis(); // Reset timer

            // Extract the substring after "Range " 
            String distanceStr = line.substring(6); 
    
            // Convert the distance string to a float
            float distance_cm = distanceStr.toFloat();
            
            if (client.connected()) {
                char payload[10];
                dtostrf(distance_cm, 5, 2, payload); 
                
                client.publish(mqtt_publish_topic, payload);
                
                Serial.print("MQTT Pub : ");
                Serial.print(payload);
                Serial.println(" cm");
            }
        }
    }
}


//Setup and Loop 
void setup() {
    Serial.begin(115200); 
    
    unsigned long startAttemptTime = millis();
    while (!Serial && millis() - startAttemptTime < 2000) {
        delay(100);
    }
    Serial.println("Serial Monitor Initialized.");
    
    setup_wifi(); 
    client.setServer(mqtt_server, 1883); // Set MQTT server details
    
    HMMDSerial.begin(HMMD_BAUDRATE, SERIAL_8N1, RX1_PIN, TX1_PIN);
    Serial.println("Serial1 Initialized on RX:" + String(RX1_PIN) + ", TX:" + String(TX1_PIN));
    
    Serial.println("Sending Configuration Hex Command...");
    // This command likely puts the sensor into the correct text/stream mode
    sendHexData(hex_to_send);
    Serial.println("Initial command sent.");
    
    Serial.println("Waiting 5 seconds for sensor to initialize and stream data...");
    delay(5000); 
    Serial.println("Start Monitoring Sensor Stream (2s Target).");
    
    // Set the initial read time to trigger the first read immediately
    lastReadTime = millis();
}
    
void loop() {
    //Maintain MQTT Connection
    if (!client.connected()) {
        reconnect();
    }
    client.loop(); 

    //Read and Publish Sensor Data (Timed)
    readAndPublishData();
    
}
