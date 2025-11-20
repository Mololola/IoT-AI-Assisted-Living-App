#include <WiFi.h>
#include <PubSubClient.h>

// Configuration, update for WiFi
const char* ssid = "iPhone";            // Your WiFi Network Name
const char* password = "hotspot1";      // Your WiFi Password
const char* mqtt_server = "X.X.X.X";    // Raspberry Pi IP Address (e.g., "172.20.10.2")

const char* mqtt_client_id = "ESP32_PIR_State_Toggle"; 
const char* mqtt_publish_topic = "home/room/presence_status"; 
const int PIR_PIN = 16;                 // GPIO pin where the PIR sensor is connected

// State Definitions
enum RoomState {
    OUT = 0,
    IN = 1
};

//Global and Objects 
WiFiClient espClient;
PubSubClient client(espClient);

RoomState currentRoomState = OUT;
bool lastPIRState = LOW; // Tracks the sensor's previous reading (HIGH/LOW)
long lastMotionTime = 0;
const long debounceDelay = 3000; // 3 seconds to ignore rapid multiple triggers

//Restore missing WiFi
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

//Restoring MQTT logic 
void reconnect() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        
        if (client.connect(mqtt_client_id)) {
            Serial.println("connected to broker!");
            client.publish("home/status", "ESP32 PIR State Online");
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" trying again in 5 seconds");
            delay(5000);
        }
    }
}

//Main PIR Logic 
void handleMotionDetection() {
    long currentTime = millis();
    
    // Read the current state of the PIR sensor
    bool currentPIRState = digitalRead(PIR_PIN);

    // Trigger Logic: Rising edge detection AND debounce check
    if (currentPIRState == HIGH && lastPIRState == LOW && (currentTime - lastMotionTime > debounceDelay)) {
        
        lastMotionTime = currentTime; // Reset the timer
        
        // Toggle the Room State
        if (currentRoomState == OUT) {
            currentRoomState = IN;
            Serial.println(">>> State Change: IN (Person walked in)");
            client.publish(mqtt_publish_topic, "IN");
        } else {
            currentRoomState = OUT;
            Serial.println(">>> State Change: OUT (Person walked out)");
            client.publish(mqtt_publish_topic, "OUT");
        }
    }

    // Update the last known state for the next loop iteration
    lastPIRState = currentPIRState;
}

//Setup and Loop 
void setup() {
    Serial.begin(115200); 
    pinMode(PIR_PIN, INPUT); // Set PIR pin as input
    
    Serial.println("PIR State Toggle Initialized.");
    
    // Calls the restored function
    setup_wifi(); 
    client.setServer(mqtt_server, 1883); 
    
    Serial.print("Initial State: ");
    Serial.println(currentRoomState == IN ? "IN" : "OUT");
}

void loop() {
    // Calls the restored function
    if (!client.connected()) {
        reconnect(); 
    }
    client.loop(); 

    handleMotionDetection();

    delay(50); // Small loop delay
}
