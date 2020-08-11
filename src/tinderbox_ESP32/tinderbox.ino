#include <Wire.h>
#include "SSD1306Wire.h" // https://github.com/ThingPulse/esp8266-oled-ssd1306
//#include "SH1106Wire.h"
#include "BluetoothSerial.h" // https://github.com/espressif/arduino-esp32
#include "font.h"
#include "spark.h"
#include <BfButton.h> //https://github.com/mickey9801/ButtonFever

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

// OLED Screen Definitions
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

// Button GPIO Definitions
#define BUTTON_1_GPIO 19
#define BUTTON_2_GPIO 18
#define BUTTON_3_GPIO 5
#define BUTTON_4_GPIO 4

BfButton btn_1(BfButton::STANDALONE_DIGITAL, BUTTON_1_GPIO, false, HIGH);
BfButton btn_2(BfButton::STANDALONE_DIGITAL, BUTTON_2_GPIO, false, HIGH);
BfButton btn_3(BfButton::STANDALONE_DIGITAL, BUTTON_3_GPIO, false, HIGH);
BfButton btn_4(BfButton::STANDALONE_DIGITAL, BUTTON_4_GPIO, false, HIGH);

// SH1106 Screen can be used in place of a SSD1306 if desired
SSD1306Wire oled(0x3c, SDA, SCL); // ADDRESS, SDA, SCL 
//SH1106Wire oled(0x3c, SDA, SCL); // ADDRESS, SDA, SCL 

BluetoothSerial SerialBT;

int selected_slot = 0;
bool connected;

void switchingPressHandler (BfButton *btn, BfButton::press_pattern_t pattern) {
  int pressed_btn_id = btn->getID();
  if(pattern == BfButton::SINGLE_PRESS) {
    switch(pressed_btn_id) {
      case BUTTON_1_GPIO:
        if (selected_slot != 1) {
          selected_slot = 1;
          changeTonePreset(LOAD_TONE_PRESET_1_CMD);
        }
        break;
      case BUTTON_2_GPIO:
        if (selected_slot != 2) {
          selected_slot = 2;
          changeTonePreset(LOAD_TONE_PRESET_2_CMD);
        }
        break;
      case BUTTON_3_GPIO:
        if (selected_slot != 3) {
          selected_slot = 3;
          changeTonePreset(LOAD_TONE_PRESET_3_CMD);
        }
        break;
      case BUTTON_4_GPIO:
        if (selected_slot != 4) {
          selected_slot = 4;
          changeTonePreset(LOAD_TONE_PRESET_4_CMD);
        }
        break;
    }
  }
}

void changeTonePreset(byte* tonePresetCmd) {
  char tone_swap_res[TONE_SWAP_DATA_SIZE] = {};
  SerialBT.write(tonePresetCmd, TONE_SWAP_DATA_SIZE);
  updateToneOnScreen();
}

void updateToneOnScreen() {
  if (selected_slot > 0) {
    oled.clear();
    oled.setFont(ArialMT_Plain_16);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 0, "Preset Tone");
    oled.setFont(Roboto_Mono_Bold_52);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 10, String(selected_slot));
    oled.display();
  } else if (selected_slot == 0) {
    oled.clear();
    oled.setFont(ArialMT_Plain_24);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 6, "Select");
    oled.drawString(64, 30, "Preset");
    oled.display();
  }
}

void displayStartup() {
  oled.init();
  oled.flipScreenVertically();
  
  oled.clear();
  oled.setFont(ArialMT_Plain_24);
  oled.setTextAlignment(TEXT_ALIGN_LEFT);
  oled.drawString(10, 12, "TinderBox");
  oled.setFont(ArialMT_Plain_16);
  oled.setTextAlignment(TEXT_ALIGN_LEFT);
  oled.drawString(24, 36, "ESP32 v0.3");
  oled.display();
  
  delay(4000);
}

void inputSetup() {   
  btn_1.onPress(switchingPressHandler);
  btn_2.onPress(switchingPressHandler);
  btn_3.onPress(switchingPressHandler);
  btn_4.onPress(switchingPressHandler);
}

void connectToAmp() {
  if(!SerialBT.begin("TinderBox", true)){
    oled.clear();
    oled.setFont(ArialMT_Plain_24);
    oled.setTextAlignment(TEXT_ALIGN_CENTER);
    oled.drawString(64, 6, "BT Init");
    oled.drawString(64, 30, "Failed!");
    oled.display();
    while(true){};
  } else {
    while(!connected) {
      oled.clear();
      oled.setFont(ArialMT_Plain_24);
      oled.setTextAlignment(TEXT_ALIGN_CENTER);
      oled.drawString(64, 20, "Connecting");
      oled.display();
      SerialBT.connect(SPARK_BT_NAME);
      connected = SerialBT.connected(10000);
      if (connected && SerialBT.hasClient()) {
        oled.clear();
        oled.setFont(ArialMT_Plain_24);
        oled.setTextAlignment(TEXT_ALIGN_CENTER);
        oled.drawString(64, 20, "Connected");
        oled.display();
        
        delay(2000);

        updateToneOnScreen();
      } else {
        connected = false;
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
}

void bt_event_callback(esp_spp_cb_event_t event, esp_spp_cb_param_t *param){
  if(event == ESP_SPP_CLOSE_EVT ){
    connected = false;
    connectToAmp();
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial);
  SerialBT.register_callback(bt_event_callback);

  connected = false;

  inputSetup();
  displayStartup();
  connectToAmp();
}

void loop() {
  btn_1.read();
  btn_2.read();
  btn_3.read();
  btn_4.read();

  if (SerialBT.available()) {
    SerialBT.read();
  }
}
