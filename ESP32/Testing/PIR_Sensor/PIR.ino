// Configurtion 
const int PIR_PIN = 2; // GPIO pin where the PIR sensor data output is connected
const long DEBOUNCE_DELAY_MS = 2000; // 2 seconds to ignore rapid multiple triggers

// Globals 
bool lastPIRState = LOW; // Tracks the sensor's raw previous reading (HIGH/LOW)
long lastMotionTime = 0; // Timestamp of the last confirmed state change
long lastPrintTime = 0; // Timestamp of the last time we printed the status (for heartbeat)

// Setup 
void setup() {
    // Start the primary serial communication (USB Monitor)
    Serial.begin(115200); 
    
    // Set the PIR pin as an input
    pinMode(PIR_PIN, INPUT); 
    
    Serial.println("PIR Sensor Serial Monitor Initialized.");
    Serial.print("PIR Sensor connected to GPIO: ");
    Serial.println(PIR_PIN);
    Serial.println("Waiting for motion...");
}

// Main Loop 
void loop() {
    long currentTime = millis();
    
    // Read the current state of the PIR sensor pin
    bool currentPIRState = digitalRead(PIR_PIN);

    // Motion Detect Start 
    // Check if the state has changed from LOW to HIGH (Motion Detected)
    if (currentPIRState == HIGH && lastPIRState == LOW) {
        
        // Only register a new event if the debounce delay has passed
        if (currentTime - lastMotionTime > DEBOUNCE_DELAY_MS) {
            
            lastMotionTime = currentTime; // Reset the motion timer
            lastPrintTime = currentTime;  // Force immediate print
            
            Serial.print("[");
            Serial.print(currentTime);
            Serial.println("] >>> MOTION DETECTED (State: HIGH)");
        }
    }
    
    // Motion Detect End 
    // Check if the state has changed from HIGH to LOW (Motion Ended/No Motion)
    else if (currentPIRState == LOW && lastPIRState == HIGH) {
        
        // This check ensures the sensor has been quiet for the debounce period
        // before confirming the "No Motion" state.
        if (currentTime - lastMotionTime > DEBOUNCE_DELAY_MS) {
            
            lastPrintTime = currentTime; // Force immediate print
            
            Serial.print("[");
            Serial.print(currentTime);
            Serial.println("] >>> MOTION ENDED (State: LOW)");
        }
    }
    
    // Periodic Heartbeart 
    // Prints the current raw state every 5 seconds for confirmation, even if nothing changes.
    if (currentTime - lastPrintTime > 5000) {
        Serial.print("[");
        Serial.print(currentTime);
        Serial.print("] Raw State: ");
        Serial.println(currentPIRState ? "HIGH (Motion)" : "LOW (No Motion)");
        lastPrintTime = currentTime;
    }

    // Update the last known raw state for the next loop iteration
    lastPIRState = currentPIRState;
    
    // Keep the loop running very fast to catch the state change immediately
    delay(50); 
}
