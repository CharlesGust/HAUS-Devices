/*
  Arduino Starter Kit example
 Project 5  - Servo Mood Indicator
 
 This sketch is written to accompany Project 5 in the
 Arduino Starter Kit
 
 Parts required:
 servo motor 
 10 kilohm potentiometer 
 2 100 uF electrolytic capacitors
 
 Created 13 September 2012
 by Scott Fitzgerald
 
 http://arduino.cc/starterKit
 
 This example code is part of the public domain 
 */

// include the servo library
#include <Servo.h>

Servo myServo;  // create a servo object 

int const potPin = A1; // analog pin used to connect the potentiometer
int potVal;  // variable to read the value from the analog pin
int potValprev = -1; // variable to check for pot oscillation
int angle;   // variable to hold the angle for the servo motor 

void setup() {
  myServo.attach(9); // attaches the servo on pin 9 to the servo object 
  Serial.begin(9600); // open a serial connection to your computer
}

void loop() {
  boolean moveit = false;
  int movement = 0;
  
  if(Serial.available() > 0) {
    moveit = true;
    angle = Serial.parseInt();
    Serial.flush();
    potVal = potValprev;
  } else {
    potVal = analogRead(potPin); // read the value of the potentiometer
    
    // has pot moved more than 2 percent?
    movement = abs(potVal - potValprev);
    if (((movement*100)/(potVal+1)) > 2) {
      //Serial.print("potValprev: ");
      //Serial.print(potValprev);
      //Serial.print(", ");
      // only move if
      moveit = true;
      potValprev = potVal;
      
      // scale the numbers from the pot 
      angle = map(potVal, 0, 1023, 0, 179);
    }
  }
  // temporarily print threshhold
  //Serial.print("movement: ");
  //Serial.print(movement);
  //Serial.print(", ");
  
  // print out the value to the serial monitor
  Serial.print("potVal: ");
  Serial.print(potVal);
  Serial.print(", ");

  // print out the angle for the servo motor 
  Serial.print("angle: ");
  Serial.println(angle); 

  if (moveit) {
    // set the servo position  
    myServo.write(angle);

    // wait for the servo to get there 
    delay(15);
  }
}



