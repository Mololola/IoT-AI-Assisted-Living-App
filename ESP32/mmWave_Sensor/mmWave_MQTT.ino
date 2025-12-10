// Define the pins for our secondary hardware serial port (Serial2)
#define RX1_PIN 18
#define TX1_PIN 19
 
void setup() {
  // Start the primary serial communication (USB Monitor)
  Serial.begin(115200);
  unsigned long startAttemptTime = millis();
  while (!Serial && millis() - startAttemptTime < 2000) {
    delay(100);
  }
  Serial.println("Serial Monitor Initialized.");
 
  // Start Serial2 for the HMMD Sensor
  Serial1.begin(115200, SERIAL_8N1, RX1_PIN, TX1_PIN);
  Serial.println("Serial1 Initialized on RX:" + String(RX1_PIN) + ", TX:" + String(TX1_PIN));
 
  // Keep the command sending for now, as you confirmed the current code works.
  // It might be putting the sensor into the correct output mode or keeping it active.
  String hex_to_send = "FDFCFBFA0800120000006400000004030201"; // Normal Mode command?
  Serial.println("Sending initial command over Serial2...");
  sendHexData(hex_to_send);
  Serial.println("Initial command sent.");
  Serial.println("Waiting for sensor readings...");
}
 
void loop() {
  // Read and process lines from Serial2
  readAndProcessSensorLines();
 
  // Small delay is fine
  delay(10);
}
 
// Original function to send command bytes - KEEPING AS IS
void sendHexData(String hexString) {
  int hexStringLength = hexString.length();
  if (hexStringLength % 2 != 0) {
    Serial.println("Error: Hex string must have an even number of characters.");
    return;
  }
  int byteCount = hexStringLength / 2;
  byte hexBytes[byteCount];
  for (int i = 0; i < hexStringLength; i += 2) {
    String byteString = hexString.substring(i, i + 2);
    byte hexByte = (byte)strtoul(byteString.c_str(), NULL, 16);
    hexBytes[i / 2] = hexByte;
  }
  // Print confirmation of what's being sent
  Serial.print("Sending ");
  Serial.print(byteCount);
  Serial.print(" bytes: ");
  for(int i=0; i<byteCount; i++) {
    if (hexBytes[i] < 16) Serial.print("0");
    Serial.print(hexBytes[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
  // Send the data
  Serial1.write(hexBytes, byteCount);
}
 
 
// *** MODIFIED FUNCTION TO READ AND PARSE LINES ***
void readAndProcessSensorLines() {
  // Check if data is available on Serial2
  while (Serial1.available() > 0) {
    // Read a line of text until a newline character (\n) is received
    // The timeout helps prevent blocking forever if a line ending is missed
    String line = Serial1.readStringUntil('\n');
 
    // Clean up the line: remove potential carriage return (\r) and leading/trailing whitespace
    line.trim();
 
    // Check if the line contains the "Range" information
    if (line.startsWith("Range ")) {
      // Extract the substring after "Range "
      String distanceStr = line.substring(6); // Start extracting after "Range " (index 6)
 
      // Convert the distance string to an integer
      int distance = distanceStr.toInt();
 
      // Print the extracted distance
      Serial.print("Detected Distance: ");
      Serial.print(distance);
      Serial.println(" cm"); // Assuming the unit is cm, adjust if needed
 
  }
}
 
}

    // 2. Read and Publish Sensor Data (Always checking sensor port)
    readAndProcessSensorLines();
    
    delay(10);
}
