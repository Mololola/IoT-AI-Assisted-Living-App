#include <WiFi.h>
#include <PubSubClient.h>

// Configuration needs to be edited 
const char* ssid = "Hyperoptic Fibre 7323";           // Your WiFi Network Name
const char* password = "UjrjR7Y4C437U4";   // Your WiFi Password
const char* mqtt_server = "192.168.1.108";     // The IP address of your Raspberry Pi (Mosquitto Broker)

const char* mqtt_client_id = "ESP32_Pressure_Sensor_01"; 
const char* mqtt_publish_topic = "home/sensor/pressure_bed"; 
const long reading_interval = 5000; // Publish data every 5 seconds (5000 ms)

// ADC Pin and Calibration for SEN-Pressure20
const int ANALOG_PIN = 4;                  // Connected to GPIO 4 (ADC2_CH0)
const float ADC_MAX_VOLTAGE = 3.3;         // ESP32 max input voltage (assuming voltage divider is used)
const int ADC_RESOLUTION = 4095;           // ESP32's default 12-bit resolution
const float SENSOR_MAX_PRESSURE = 2.0;     // Max pressure in Bar for SEN-Pressure20

//Global and Objects 
WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0; 

// Sensor Readings 
// Reads the analog sensor and converts the voltage to a pressure value in Bar.
float readPressureValue() {
    // Read the raw analog value (0-4095)
    int rawValue = analogRead(ANALOG_PIN);

    // Convert the raw ADC reading to a voltage (0.0V to 3.3V)
    // IMPORTANT: Ensure the sensor output is safely scaled down to 3.3V max!
    float voltage = rawValue * (ADC_MAX_VOLTAGE / ADC_RESOLUTION);

    // Convert Voltage to Pressure (Bar)
    // Assuming a linear response where ADC_MAX_VOLTAGE (3.3V) corresponds to SENSOR_MAX_PRESSURE (2.0 Bar)
    float pressure_bar = (voltage / ADC_MAX_VOLTAGE) * SENSOR_MAX_PRESSURE; 

    return pressure_bar; // Returns pressure in Bar
}

//WiFi set up 
void setup_wifi() {
  delay(10);
  Serial.print("Connecting to ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  // Wait until connected to WiFi
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// MQTT reconnection logic 
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

//Setup and Loop 
void setup() {
  Serial.begin(115200); 
  
  // Set ADC 2 to a known attenuation and resolution for reliable readings
  analogReadResolution(12); // Set resolution to 12 bits (0-4095)

  Serial.println("Analog Pressure Sensor Initialized on GPIO 4.");
  
  setup_wifi();
  client.setServer(mqtt_server, 1883); 
}

void loop() {
  // 1. Maintain connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); 

  long now = millis();
  
  // 2. Check if the publish interval has elapsed
  if (now - lastMsg > reading_interval) {
    lastMsg = now;
    
    // 3. Read the pressure value
    float pressure = readPressureValue(); 
    
    // 4. Convert float to a string payload (e.g., "1.54")
    char payload[10];
    // dtostrf(value, min_width, num_digits_after_decimal, buffer)
    dtostrf(pressure, 6, 2, payload); 
    
    // 5. Publish the value to the MQTT broker
    client.publish(mqtt_publish_topic, payload);
    
    // 6. Print to Serial Monitor for local debugging
    Serial.print("Published [");
    Serial.print(mqtt_publish_topic);
    Serial.print("] Value: ");
    Serial.print(payload);
    Serial.println(" Bar");
  }
}