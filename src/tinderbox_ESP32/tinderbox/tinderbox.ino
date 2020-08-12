#include <Wire.h>
#include "SSD1306Wire.h" // https://github.com/ThingPulse/esp8266-oled-ssd1306
//#include "SH1106Wire.h"
#include "BluetoothSerial.h" // https://github.com/espressif/arduino-esp32
#include "font.h"
#include "spark.h"
#include <BfButton.h> //https://github.com/mickey9801/ButtonFever

// Device Info Definitions
const String DEVICE_NAME = "TinderBox";
const String VERSION = "0.3.1";

// Check ESP32 Bluetooth configuration
#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

// OLED Screen Definitions (SH1106 driven screen can be used in place of a SSD1306 screen, if desired)
SSD1306Wire oled(0x3c, SDA, SCL); // ADDRESS, SDA, SCL 
//SH1106Wire oled(0x3c, SDA, SCL); // ADDRESS, SDA, SCL 

// Button GPIO and Object Definitions
#define NUM_OF_BUTTONS 4

#define BUTTON_1_GPIO 19
#define BUTTON_2_GPIO 18
#define BUTTON_3_GPIO 5
#define BUTTON_4_GPIO 4
const int BUTTON_GPI0_LIST[] = {BUTTON_1_GPIO, BUTTON_2_GPIO, BUTTON_3_GPIO, BUTTON_4_GPIO}; 

BfButton btn_1(BfButton::STANDALONE_DIGITAL, BUTTON_1_GPIO, false, HIGH);
BfButton btn_2(BfButton::STANDALONE_DIGITAL, BUTTON_2_GPIO, false, HIGH);
BfButton btn_3(BfButton::STANDALONE_DIGITAL, BUTTON_3_GPIO, false, HIGH);
BfButton btn_4(BfButton::STANDALONE_DIGITAL, BUTTON_4_GPIO, false, HIGH);
BfButton BTN_LIST[] = {btn_1, btn_2, btn_3, btn_4};

// ESP32 Bluetooth Serial Object
BluetoothSerial SerialBT;

// Device State Variables
int selected_tone_preset;
bool connected;

void switchingPressHandler (BfButton *btn, BfButton::press_pattern_t pattern) {
  // If single press detected
  if(pattern == BfButton::SINGLE_PRESS) {
    int pressed_btn_gpio = btn->getID();
    // Determine which button was pressed
    for(int i = 0; i< NUM_OF_BUTTONS; i++) {
      // Don't send a cmd to change the tone preset if it is already selected
      if (pressed_btn_gpio == BUTTON_GPI0_LIST[i] && selected_tone_preset != i+1) {
        selected_tone_preset = i+1;
        sendLoadTonePresetCmd(LOAD_TONE_PRESET_LIST[i]);
      }
    }
  }
}

void sendLoadTonePresetCmd(byte* loadTonePresetCmd) {
  // Send load tone preset command to amp
  SerialBT.write(loadTonePresetCmd, LOAD_TONE_PRESET_CMD_SIZE);
  // Update device screen with the new tone preset selection
  updateTonePresetScreen();
}

void updateTonePresetScreen() {
  // If a tone selection has been made (i.e. selected_tone_preset is not zero)
  if (selected_tone_preset > 0) {
    // Show "Tone Preset <selection_num>" message on device screen
    oled.clear();
    oled.setFont(ArialMT_Plain_16);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 0, "Tone Preset");
    oled.setFont(Roboto_Mono_Bold_52);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 10, String(selected_tone_preset));
    oled.display();
  } else if (selected_tone_preset == 0) { // Else if no tone selection has been made yet
    // Show "Select Preset" message on device screen
    oled.clear();
    oled.setFont(ArialMT_Plain_24);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 6, "Select");
    oled.drawString(64, 30, "Preset");
    oled.display();
  }
}

void displayStartup() {
  // Initialize device OLED display, and flip screen, as OLED library starts "upside-down" (for some reason?)
  oled.init();
  oled.flipScreenVertically();

  // Show "TinderBox ESP v<version_num>" message on device screen
  oled.clear();
  oled.setFont(ArialMT_Plain_24);
  oled.setTextAlignment(TEXT_ALIGN_CENTER);
  oled.drawString(64, 12, DEVICE_NAME);
  oled.setFont(ArialMT_Plain_16);
  oled.setTextAlignment(TEXT_ALIGN_CENTER);
  oled.drawString(64, 36, "ESP32 v" + VERSION);
  oled.display();
  
  delay(4000);
}

void inputSetup() {
  // Setup callback for single press detection on all four input buttons
  for(int i = 0; i < NUM_OF_BUTTONS; i++) {
    BTN_LIST[i].onPress(switchingPressHandler);
  }
}

void btEventCallback(esp_spp_cb_event_t event, esp_spp_cb_param_t *param){
  // On BT connection close
  if(event == ESP_SPP_CLOSE_EVT ){
    // TODO: Until the cause of connection instability (compared to Pi version) over long durations 
    // is resolved, this should keep your pedal and amp connected fairly well by forcing reconnection
    // in the main loop
    connected = false;
    selected_tone_preset = 0;
  }
}

void btInit() {
  // Register BT event callback method
  SerialBT.register_callback(btEventCallback);
  if(!SerialBT.begin(DEVICE_NAME, true)){ // Detect for BT failure on ESP32 chip
    // Show "BT Init Failed!" message on device screen
    oled.clear();
    oled.setFont(ArialMT_Plain_24);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 6, "BT Init");
    oled.drawString(64, 30, "Failed!");
    oled.display();
    
    // Loop infinitely until device shutdown/restart
    while(true){};
  }
}

void connectToAmp() {
  // Loop until device establishes connection with amp
  while(!connected) {
    // Show "Connecting" message on device screen
    oled.clear();
    oled.setFont(ArialMT_Plain_24);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 20, "Connecting");
    oled.display();

    // Attempt BT connection to amp
    connected = SerialBT.connect(SPARK_BT_NAME);

    // If BT connection with amp is successful
    if (connected && SerialBT.hasClient()) {
      // Show "Connected" message on device screen
      oled.clear();
      oled.setFont(ArialMT_Plain_24);
      oled.setTextAlignment(TEXT_ALIGN_CENTER);
      oled.drawString(64, 20, "Connected");
      oled.display();
      
      delay(2000);
      
      // Display inital Tone Preset Screen
      updateTonePresetScreen();
    } else { // If amp is not found, or other connection issue occurs
      // Set 'connected' to false to continue amp connection loop
      connected = false;

      // Show "Failed Rescanning" message on device screen
      oled.clear();
      oled.setFont(ArialMT_Plain_24);
      oled.setTextAlignment(TEXT_ALIGN_CENTER);
      oled.drawString(64, 6, "Failed");
      oled.drawString(64, 30, "Rescanning");
      oled.display();
      
      delay(4000);
    }
  }
}

void setup() {
  // Start serial debug console monitoring
  Serial.begin(115200);
  while (!Serial);

  // Set initial device state values
  connected = false;
  selected_tone_preset = 0;

  // Setup Device I/O
  inputSetup();
  displayStartup();
  btInit();
}

void loop() {
  // Check if amp is connected to device
  if(!connected) {
    // If not, attempt to establish a connection
    connectToAmp();
  } else { // If amp is connected to device over BT
    // Scan all input buttons for presses
    for(int i = 0; i < NUM_OF_BUTTONS; i++) {
      BTN_LIST[i].read();
    }
  
    // Read in response data from amp, to clear BT message buffer
    if (SerialBT.available()) {
      SerialBT.read();
    }
  }
}
