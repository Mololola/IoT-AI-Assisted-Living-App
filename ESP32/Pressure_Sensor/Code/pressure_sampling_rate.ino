#include <WiFi.h>
#include <PubSubClient.h>

// ------------------------------------
// 1. CONFIGURATION (*** CRITICAL: UPDATE THESE VALUES ***)
// ------------------------------------
const char* ssid = "Hyperoptic Fibre 7323";           // Your WiFi Network Name
const char* password = "UjrjR7Y4C437U4";   // Your WiFi Password
const char* mqtt_server = "192.168.1.108";     // The IP address of your Raspberry Pi (Mosquitto Broker)

const char* mqtt_client_id = "ESP32_Pressure_Sensor_01"; 
const char* mqtt_publish_topic = "home/bedroom/pressure"; 

// --- SAMPLING & PUBLISHING RATES (OPTIMIZED FOR BATTERY LIFE) ---
const long SAMPLE_RATE_MS = 1000;    // Sample ADC every 1 second (1Hz - High enough for reliability)
const long PUBLISH_INTERVAL_MS = 30000; // Publish over MQTT every 30 seconds (Scheduled Report)
const float PRESSURE_THRESHOLD_BAR = 0.05; // Publish immediately if pressure changes by 0.05 Bar

// ADC Pin and Calibration for SEN-Pressure20
const int ANALOG_PIN = 4; 
const float ADC_MAX_VOLTAGE = 3.3;
const int ADC_RESOLUTION = 4095; 
const float SENSOR_MAX_PRESSURE = 2.0; 

// ------------------------------------
// 2. GLOBALS & OBJECTS
// ------------------------------------
WiFiClient espClient;
PubSubClient client(espClient);
long lastSampleTime = 0; 
long lastPublishTime = 0; 
float lastPublishedPressure = -1.0; // Stores the last value successfully published

// ------------------------------------
// 3. SENSOR READING FUNCTION
// ------------------------------------
float readPressureValue() {
    int rawValue = analogRead(ANALOG_PIN);
    float voltage = rawValue * (ADC_MAX_VOLTAGE / ADC_RESOLUTION);
    float pressure_bar = (voltage / ADC_MAX_VOLTAGE) * SENSOR_MAX_PRESSURE; 

    return pressure_bar; // Returns pressure in Bar
}

// ------------------------------------
// 4. NETWORK FUNCTIONS (Unchanged)
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
            client.publish("home/status", "ESP32 Pressure Sensor Online");
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" trying again in 5 seconds");
            delay(5000);
        }
    }
}

// ------------------------------------
// 5. PUBLISHING LOGIC (NEW)
// ------------------------------------
void publishPressure(float pressure) {
    if (!client.connected()) return;

    // 1. Convert float to string payload
    char payload[10];
    dtostrf(pressure, 6, 2, payload); 
    
    // 2. Publish the value to the MQTT broker
    client.publish(mqtt_publish_topic, payload);
    
    // 3. Update status variables
    lastPublishedPressure = pressure;
    lastPublishTime = millis();
    
    // 4. Debug output
    Serial.print("MQTT Pub: ");
    Serial.print(payload);
    Serial.println(" Bar");
}


// ------------------------------------
// 6. SETUP & LOOP
// ------------------------------------
void setup() {
    Serial.begin(115200); 
    
    // Set ADC 2 to a known attenuation and resolution for reliable readings
    analogReadResolution(12); 

    Serial.println("Analog Pressure Sensor Initialized on GPIO 4.");
    
    setup_wifi();
    client.setServer(mqtt_server, 1883); 
    
    // Initialize last pressure to an impossible value to ensure first reading is published
    lastPublishedPressure = -100.0; 
}

void loop() {
    // 1. Maintain connection
    if (!client.connected()) {
        reconnect();
    }
    client.loop(); 

    // 2. Check if it's time to sample the ADC (1Hz rate)
    long now = millis();
    if (now - lastSampleTime >= SAMPLE_RATE_MS) {
        lastSampleTime = now;
        
        float currentPressure = readPressureValue(); 

        // 3. PUBLISH CONDITION CHECK
        
        // A. Check for forced scheduled publish (30 seconds)
        bool publishScheduled = (now - lastPublishTime >= PUBLISH_INTERVAL_MS);
        
        // B. Check for threshold-based publish (significant change)
        float pressureDelta = abs(currentPressure - lastPublishedPressure);
        bool publishThreshold = (pressureDelta >= PRESSURE_THRESHOLD_BAR);
        
        // Publish if either condition is met
        if (publishScheduled || publishThreshold) {
            publishPressure(currentPressure);
        } else {
            // Optional debug to show reading, but not publishing
            // Serial.print("Sampled: "); Serial.println(currentPressure, 2);
        }
    }
}