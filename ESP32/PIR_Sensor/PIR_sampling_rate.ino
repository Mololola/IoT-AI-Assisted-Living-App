#include <WiFi.h>
#include <PubSubClient.h>

// ------------------------------------
// 1. CONFIGURATION (*** CRITICAL: UPDATE THESE VALUES ***)
// ------------------------------------
const char* ssid = "Hyperoptic Fibre 7323";            // Your WiFi Network Name
const char* password = "UjrjR7Y4C437U4";      // Your WiFi Password
const char* mqtt_server = "192.168.1.108";     // Raspberry Pi IP Address

const char* mqtt_client_id = "ESP32_PIR_Agent_02"; 
const char* mqtt_publish_topic = "home/bedroom/PIR"; 

// --- PIR PIN AND DEBOUNCING ---
const int PIR_PIN = 2;                  // GPIO pin where the PIR sensor is connected
const long DEBOUNCE_DELAY_MS = 3000;    // 3 seconds to ignore rapid multiple triggers

// State Definitions
enum RoomState {
    OUT = 0, // No confirmed presence
    IN = 1   // Confirmed presence
};

// ------------------------------------
// 2. GLOBALS & OBJECTS
// ------------------------------------
WiFiClient espClient;
PubSubClient client(espClient);

RoomState currentRoomState = OUT;
bool lastPIRState = LOW; // Tracks the sensor's raw previous reading (HIGH/LOW)
long lastMotionTime = 0; // Timestamp of the last confirmed motion event


// --- Function Prototypes ---
void publishState(const char* state_str);
void setup_wifi();
void reconnect();


// ------------------------------------
// 3. WIFI & MQTT CONNECTION FUNCTIONS (Standard Code)
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

void reconnect() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        
        if (client.connect(mqtt_client_id)) {
            Serial.println("connected to broker!");
            client.publish("home/status", "ESP32 PIR Sensor Online");
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" trying again in 5 seconds");
            delay(5000);
        }
    }
}


// ------------------------------------
// 4. PUBLISHING LOGIC
// ------------------------------------
void publishState(const char* state_str) {
    if (client.connected()) {
        client.publish(mqtt_publish_topic, state_str);
        Serial.print("MQTT Pub: State changed to ");
        Serial.println(state_str);
    }
}


// ------------------------------------
// 5. MAIN LOGIC: Event-Driven State Handler
// ------------------------------------
void handleMotionDetection() {
    long currentTime = millis();
    
    // Read the current state of the PIR sensor pin
    bool currentPIRState = digitalRead(PIR_PIN);

    // --- RISING EDGE DETECTION (Motion Start) ---
    // Condition 1: Sensor signal just changed from LOW to HIGH.
    // Condition 2: Debounce time has passed since the last confirmed event.
    if (currentPIRState == HIGH && lastPIRState == LOW && (currentTime - lastMotionTime > DEBOUNCE_DELAY_MS)) {
        
        lastMotionTime = currentTime; // Reset the debounce timer
        
        // --- TOGGLE ROOM STATE ---
        if (currentRoomState == OUT) {
            currentRoomState = IN;
            Serial.println(">>> State Change: IN (Movement Detected)");
            publishState("IN");
        } else {
            currentRoomState = OUT;
            Serial.println(">>> State Change: OUT (Movement Detected - Toggling out)");
            publishState("OUT");
        }
    }

    // Update the last known raw state for the next loop iteration
    lastPIRState = currentPIRState;
}

// ------------------------------------
// 6. SETUP & LOOP
// ------------------------------------
void setup() {
    Serial.begin(115200); 
    pinMode(PIR_PIN, INPUT); // Set PIR pin as input
    
    Serial.println("PIR State Toggle Initialized.");
    
    setup_wifi();
    client.setServer(mqtt_server, 1883); 
    
    Serial.print("Initial State: ");
    Serial.println(currentRoomState == IN ? "IN" : "OUT");
}

void loop() {
    // 1. Maintain MQTT Connection
    if (!client.connected()) {
        reconnect();
    }
    client.loop(); 

    // 2. Handle Logic
    handleMotionDetection();

    // The loop runs quickly, providing a high polling rate for responsiveness (100ms target).
    delay(100); 
}