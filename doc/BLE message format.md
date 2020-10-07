# Reverse engineering the BLE message format used for app <-> amp communications

Data was collected using Bluetooth traffic snooping on Android phone. It was a surprise that some phones have problems capturing complete traffic (Nokia 6.1) while some have no problems (Samsung).

## Data frame format

Each data packet starts with a header:

| Offset | 00 | 01 | 02 | 03 |
|--------|----|----|----|----|
| Data   | 01 | fe | 00 | 00 |


The next two bytes are depending on direction:

Receive (from Spark):

| Offset | 04 | 05 |
|--------|----|----|
| Data   | 41 | ff |


Send (to Spark):

| Offset | 04 | 05 |
|--------|----|----|
| Data   | 53 | fe |

At offset 0x06, the data size for this packet is sent (including the size of 6-byte header) 

| Offset |  06  | 
|--------|------|
| Data   | size |

The maximum length of the data received from the Spark is 0x6a,
longer messages are split into multiple packets.

There seems to be no such limit for the data sent to the Spark.
TODO: verify how completely new preset is sent.

Next 9 bytes are always zeroes:

| Offset | 07 | 08 | 09 | 0A | 0B | 0C | 0D | 0E | 0F |
|--------|----|----|----|----|----|----|----|----|----|
| Data   | 00 | 00 | 00 | 00 | 00 | 00 | 00 | 00 | 00 |

### Case of first packet / single packet response:

The next two bytes are fixed:

| Offset | 10 | 11 |
|--------|----|----|
| Data   | f0 | 01 |


At offset 0x12 (and most likely offset 0x13 as well), sequence number is sent

| Offset |  12              |  13                  |
|--------|------------------|----------------------|
| Data   |  sequence number |  sequence number (?) |

It is known (from the existing working code) that this number is never checked by the amp.

Command is encoded at offset 0x14 - 0x15

| Offset |  14       |  15       |
|--------|-----------|-----------|
| Data   | operation | parameter |

It may be followed by zero, one or three arguments (pedal name, control ID and control value)

### Response continuation

For a response that does not fil into a single packet, the next bytes
starting at offset 0x10 are just continuation of the message (no additional prefixes or sequence number.

### Last packet in response / single packet response

The last data packet ends with a trailer

| Offset | xx |
|--------|----|
| Data   | f7 |

## Arguments

Arguments are defined by their type (1 byte) and variable length value.

### Argument types

| Value | Type |
|-------|------|
| 00    | Integer number
| 01    | Sequence (?)
| 02    | String list
| 42    | Boolean "True"
| 43    | Boolean "False"


### Integer number

Fixed value length -- 2 bytes, BigEndian

### String list

One of more ASCII strings encoded using following algorithm:

| Offset | 00     | 01          | 02 | 03 | 04 | 05 | 06 | 07 | 08 | ... | 0f | 10 | ... |
|--------|--------|-------------|----|----|----|----|----|----|----|-----|----|----|-----|
| Data   | Length | 0x20+Length | b1 | b2 | b3 | b4 | b5 | xx | b6 | ... | bC | xy | ... |

where 
 - first byte is the string length
 - second byte is always string length + 0x20 (control value?)
 - b1.... are ASCII characters of the string
 - xx / xy looks like 1 << "amount of bytes remaining", that will be 
   - 0x01 when no characters remaining
   - 0x2...0x40 depending on number of characters remaining
   - 0x00 when all 7 characters are following and at last one more remains for the next 8 bytes block.

### Booleans

Have no value bytes associated with them.


## Operation types

| Value | Operation  |
|-------|------------|
|  00   | Info       |
|  01   | Set        |
|  02   | Get        |
|  03   | Response(?)|
|  f0   | Sequence(?)| 


## INFO Operation

The only known operation is 

02 23  - Get hardware ID


## SET operation

Following SET operations are known:

| Parameter |                       |
|-----------|-----------------------|
| 02        | Change value
| 06        | Change pedal
| 15        | Enable/Disable a pedal
| 38        | Change to preset

### 02 Change value

This command has XX arguments:
 - String list - Pedal name
 - Some extra values that should have parameter number and parameter value encoded.

### 06 Change pedal

This command has two arguments:
 - String list - Source pedal name, Target pedal name
 - an extra value

### 15 Pedal Enable/Disable

This command has two arguments: 
 - String list - Pedal name (NOT the identifier of the position in the chain - you should query current config before changing the state).
 - Boolean True or Boolean False.
   There is no consensus on what "True" value means, for different positions (maybe even pedals?) it is different.

   | Position       | Active     | Disabled   |
   |----------------|------------|------------|
   | 0 (noise gate) | 42 (True)  | 43 (False) |
   | 1 (compressor) | 42 (True)  | 43 (False) |
   | 2 (distortion) | 43 (False) | 42 (True)  |
   | 3 (amp)        | -          | -          |
   | 4 (chorus)     | 43 (False) | 42 (True)  |
   | 5 (delay)      | 43 (False) | 42 (True)  |

### 38 Change to preset

This command has one argument:
 - Integer number - Preset number starting 0 (the values are 00 00 - 00 03)

## GET Operations

Following GET operations are known:

| Parameter |                       |
|-----------|-----------------------|
|  01       | Get preset configuration
|  02       |
|  11       | Get device name

### 01 Get preset configuration

Multiple arguments, only first one is actually used

 - Integer number - Preset number starting 0, or 0x0100 for "current"
 - 34x "0x00" (that is 11x "Integer number, value 0" + 0x00)

## "ACK" packets

After a successful operation, amp sends back an "ack" packet with

Command = 0x00 (info)
Parameter = 0x04
Value = 0x15
