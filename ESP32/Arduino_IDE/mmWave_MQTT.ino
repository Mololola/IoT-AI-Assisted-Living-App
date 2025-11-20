// Required for string to hex conversion
#include <stdlib.h> 
#include <WiFi.h>      // For Wi-Fi Connectivity
#include <PubSubClient.h> // For MQTT Protocol


// Configuration - Update o
const char* ssid = "iPhone";            // Your WiFi Network Name
const char* password = "hotspot1";      // Your WiFi Password

// FIX THIS: Replace with the ACTUAL IP address of your Raspberry Pi (Mosquitto Broker)
const char* mqtt_server = "X.X.X.X";    

const char* mqtt_client_id = "ESP32_HMMD_MQTT_01"; 
const char* mqtt_publish_topic = "home/sensor/distance_cm"; 

// ESP32 Pin definitions 
#define RX1_PIN 18
#define TX1_PIN 19
#define HMMD_BAUDRATE 115200 

// HMMD command 
String hex_to_send = "FDFCFBFA0800120000006400000004030201"; 

//Globals and Objects 
HardwareSerial HMMDSerial(1); // Custom serial object for sensor communication
WiFiClient espClient;         // Wi-Fi client used by MQTT
PubSubClient client(espClient); // MQTT client

// Function Prototype 
void sendHexData(String hexString);
void readAndProcessSensorLines();
void setup_wifi();
void reconnect();

//Wifi Setup 
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

//MQTT reconnection logic 
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


// Main Logic 
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


// Reader and Publisher 
void readAndProcessSensorLines() {
    // Check if data is available on the sensor's serial port
    while (HMMDSerial.available() > 0) {
        // Read a line of text until a newline character (\n) is received
        String line = HMMDSerial.readStringUntil('\n');
    
        // Clean up the line
        line.trim();
    
        // Check if the line contains the "Range" information
        if (line.startsWith("Range ")) {
            // Extract the substring after "Range "
            String distanceStr = line.substring(6); 
    
            // Convert the distance string to an integer
            int distance = distanceStr.toInt();
            
            // --- MQTT PUBLISHING ---
            if (client.connected()) {
                // Convert integer distance back to a character array for MQTT payload
                char payload[10];
                itoa(distance, payload, 10); 
                
                // Publish the distance to the MQTT broker
                client.publish(mqtt_publish_topic, payload);
                
                Serial.print("MQTT Pub: ");
                Serial.print(payload);
                Serial.println(" cm");
            }

            // Print to Serial Monitor for local debugging
            Serial.print("Detected Distance: ");
            Serial.print(distance);
            Serial.println(" cm");
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
    Serial.println("Start Monitoring Sensor Stream.");
}
    
void loop() {
    // 1. Maintain MQTT Connection (Must be called frequently)
    if (!client.connected()) {
        reconnect();
    }
    client.loop(); 

    // 2. Read and Publish Sensor Data (Always checking sensor port)
    readAndProcessSensorLines();
    
    delay(10);
}
