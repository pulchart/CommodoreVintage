# Quieting the Commodore C1581 Disk Drive

Recently, I purchased a Commodore c1581 disk drive on eBay to add to my collection of vintage computers. For those unfamiliar, the c1581 is a floppy disk drive released in the late 1980s by Commodore, designed to work with Commodore 8bit systems (like Commodore c64 or c128). It uses 3.5" floppy disks, a popular storage medium during that era.

As I began using the c1581, I was surprised by how loud it was. The noise comes primarily from the **stepper motor**, which moves the drive head to specific positions on the disk to read or write data. This movement is controlled by Type I commands, a specific class of low-level control commands defined by the floppy disk controller, such as the WD1770, WD1772, or VL1772 used in the c1581.

To provide some technical context, Type I commands are used for **head positioning** operations. They include instructions to seek a specific track, step the head incrementally forward or backward, and recalibrate the head to the zero track (the home position). These commands are essential for navigating the disk's tracks to locate and access the desired data. However, they also produce noise, particularly when the head is moved rapidly or repeatedly.

While Type I commands are executed whenever the drive moves its heads, the noise is especially noticeable during the **power-up sequence**. At startup, the drive performs a specific recalibration pattern to ensure the head is properly aligned, which involves moving it to its physical limits. This pattern results in a loud and repetitive clicking or clunking sound. Although the drive is fully operational, this noise can be jarring.

For this project, I aim to investigate the cause of the noise during the power-up sequence and general head movements. I suspect this behavior might be a result of a firmware quirk, mechanical misalignment, or an unintentional bug. The goal is to identify and implement a fix to resolve the issue while maintaining the drive's original functionality and compatibility.

# Documentation and References

The following resources were invaluable in understanding the C1581's internals and diagnosing the root cause of the issue:
* [The 1581 Toolkit](https://www.lyonlabs.org/commodore/onrequest/The_1581_Toolkit.pdf)
* [C1581 Service Manual (Devili.iki.fi)](https://www.devili.iki.fi/Computers/Commodore/C1581/Service_Manual/Contents.html)
* [C1581 Service Manual (Zimmers.net)](http://www.zimmers.net/anonftp/pub/cbm/schematics/drives/new/1581/1581_Service_Manual_314982-01_(1987_Jun).pdf)
* [C1581 Firmware Version Comparison (Ninja/The Dreams)](http://unusedino.de/ec64/technical/aay/c1581/romver.htm)
* [C1581 Firmware Binaries and Source Code (Zimmers.net)](http://www.zimmers.net/anonftp/pub/cbm/firmware/drives/new/1581/index.html)
* [Panasonic JU-363 Brochure](http://www.bitsavers.org/pdf/panasonic/floppy/brochures/Panasonic_JU-363_364_JU-386_JU-394_Brochure_Mar87.pdf)
* [WD1770/WD1772 Controller Datasheet Preliminary](https://datasheet4u.com/datasheet-pdf/WesternDigital/WD1770/pdf.php?id=1311812)
* [WD1770/WD1772 Controller Datasheet Final](http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/wd177x/index.html)
* [VL1772 Controller Datasheet](https://datasheet4u.com/datasheet-pdf/VLSITechnology/VL1772-02/pdf.php?id=555949)
* [1581 Disk Drive - another look at HW/SW (floobydust)](http://forum.6502.org/viewtopic.php?f=4&t=5714)

# Understanding the Issue

The noise originates from the stepper motor, which moves the drive head based on Type I commands of the WD1770/WD1772 (or the equivalent VL1772) controller. The service manual mentions a jumper, J1, which should be closed for the WD1770 and open for the WD1772. However, it doesn’t elaborate on the implications of this setting.

A key clue in this investigation came from "The 1581 Toolkit" documentation, specifically the "1581 Bugs" section. One known bug is described as follows:
> The first one involved an improperly grounded jumper (Jl) on the PC board inside the 1581 disk drive. Allows the drive to use the
6 ms step rate.

The 6ms step rate is optional and only applies when J1 is closed. But is 6ms correct for the step motor? If J1 is open, what step rate is being used? And what is the expected step rate for the floppy's step motor within the drive?

This issue seems to stem from a combination of factors:
* **Software**: The firmware sending Type I commands to the WD177x controller.
* **Hardware**: The C1581 configuration, including the WD1770/WD1772/VL1772 controller and the J1 jumper setting.
* **Floppy drive mechanism**: Misalignment of the step motor's required step rate in milliseconds.

Upon opening my C1581 chassis, I confirmed the issue described in the documentation. My model uses a WD1770 controller with the J1 jumper set to open—an undesirable combination. This configuration means the step rate is not 6ms but an unknown, likely higher, value.

The floppy mechanism in my C1581 is a JU-363. According to the JU-363 Brochure, the track-to-track time (desired step rate) is 3ms. To rule out the drive mechanism as the root cause, I tested other drives from my Amiga systems (JU-257, FZ-354, D357T2), all of which exhibited the same step motor behavior. This confirms that the JU-363 is not the source of the problem.

Let's take a closer look at the firmware code of the C1581 related to Type I commands (restore, seek, step, step-in, step-out) found in `MROUT.SRC`:
```
lda  #$08	; setup wd177x commands
sta  wdrestore
lda  #$18
sta  wdseek
lda  #$28
sta  wdstep   
lda  #$48
sta  wdstepin		
lda  #$68
sta  wdstepout
lda  #$88
...
```
Later, these values are incremented by +1 based on the J1 jumper configuration (open or closed):
```
...
lda  todlsb
bne  2$		; default wd1770

inc  wdrestore
inc  wdseek   
inc  wdstep   
inc  wdstepin		
inc  wdstepout
```
This results in values of either `0x.8` or `0x.9` depending on the J1 jumper setting. The first two bits (r0, r1) in the Type I commands determine the step rate:
* `r0=0`, `r1=0` when jumper J1 is closed (corresponding to `0x.8`)
* `r0=1`, `r1=0` when jumper J1 is open (corresponding to `0x.9`)

Now, let’s review the datasheets for the WD1770, WD1772, and VL1772 to understand their step rates. The information is somewhat confusing, and I believe this is a key factor contributing to the "motor volume" issue:

| r1 | r0 | WD1770 | WD1772 (prelimirary) | WD1772 (final) | VL1772 | c1581 Firmware |
| -- | -- | ------ | -------------------- | -------------- | ------ | ---------------|
| 0  | 0  | 6ms    | 2ms                  | 6ms            | 6ms    | J1 closed      |
| 0  | 1  | 12ms   | 3ms                  | 12ms           | 12ms   | J1 open        |
| 1  | 0  | 20ms   | 5ms                  | 2ms            | 2ms    | n/a            |
| 1  | 1  | 30ms   | 6ms                  | 3ms            | 3ms    | n/a            |

Now I understand! The J1 jumper isn't for selecting between WD1770 and WD1772 controllers but for switching between two step rates. The firmware supports the first two combinations. I have a WD1770 with J1 open, which results in a 12ms step rate for a floppy mechanism designed for 3ms. No wonder the step motor is so loud—it’s operating at 12ms instead of the expected 3ms! I've pinpointed the root cause.

By closing the J1 jumper, I was able to achieve the lowest possible step rate of 6ms with my WD1770, and this improved the drive's behavior. The mechanism is quieter—still not perfect, but much better than before. Unfortunately, further improvement isn’t possible with the WD1770 since lower step rates aren’t supported.

# Solution

To achieve the desired 3ms step rate for the JU-363, I need a different floppy controller chip, such as the WD1772 or VL1772. Fortunately, I have one available in my Commodore C1571 drive. As an alternative to the WD1770, I checked the C1571's source code and found it supports a single-step rate combination of `r0=r1=0`, which corresponds to a 6ms step rate. Therefore, the WD1770 is sufficient for the C1571, allowing me to swap the VL1772 into the C1581 and use the WD1770 in the C1571.

However, I’ve identified a bug in the firmware, which was already hinted at as the root of the issue—confusion between the "preliminary" and "final" datasheets for the WD1772.

The firmware expects a 6ms step rate, with J1 closed, as the optimal setting for the WD1770. For the WD1772, it uses a 3ms step rate, with J1 open, based on the preliminary datasheet:

| r1 | r0 | **WD1770** | **WD1772 (prelimirary)** | c1581 Firmware |
| -- | -- | ---------- | ------------------------ | ---------------|
| 0  | 0  | **6ms**    | 2ms                      | J1 closed      |
| 0  | 1  | 12ms       | **3ms**                  | J1 open        |

This does not accurately represent the actual or final state; the correct configuration for the WD1770/WD1772 components is as follows:

| r1 | r0 | **WD1770** | **WD1772/VL1772** | c1581 Firmware |
| -- | -- | ---------- | ----------------- | ---------------|
| 0  | 0  | **6ms**    | 6ms               | J1 closed      |
| 0  | 1  | 12ms       | **12ms**          | J1 open        |

With the current setup, the system achieves a 6ms step rate when J1 is closed or a 12ms step rate when J1 is open, as specified in the WD1772 datasheet. This behavior remains consistent regardless of whether the controller is WD1770 or WD1772.

To enable the desired behavior, I need to replace the WD1770 with the VL1772 and patch the ROM file to support faster step rates in the Type I command. The updated ROM will function correctly only with the WD1772 or VL1772. The patched firmware should implement the following behavior:

| r1 | r0 | WD1770 | WD1772/VL1772 | c1581 patched firmware |
| -- | -- | ------ | ------------- | ---------------------- |
| 0  | 0  | 6ms    | 6ms           | n/a                    |
| 0  | 1  | 12ms   | 12ms          | n/a                    |
| 1  | 0  | 20ms   | 2ms           | J1 closed              |
| 1  | 1  | 30ms   | 3ms           | J1 open                |

To implement this, I need to modify the ROM file by replacing `0x.8` values with `0x.A` in the code or binary file.
* `r0=0`, `r1=1` when jumper J1 is closed (corresponding to `0x.a`)
* `r0=1`, `r1=1` when jumper J1 is open (corresponding to `0x.b`)

In the assembler, this should appear as:
```
lda  #$0a	; setup wd177x commands
sta  wdrestore
lda  #$1a
sta  wdseek
lda  #$2a
sta  wdstep   
lda  #$4a
sta  wdstepin		
lda  #$6a
sta  wdstepout
lda  #$8a
```
# Patching ROM code

I decided to modify the binary ROM file directly since I don’t have the ability to compile the source code.

I’ll use the latest ROM version, 318045-02, which includes the most recent fixes. This version disables the initial SELF TEST DIAGNOSTICS, allowing the C1581 to boot without recalculating the checksum (third byte in the binary file) or verifying the signature bytes (first two bytes). However, I plan to re-enable the SELF TEST DIAGNOSTICS later and correct the checksum and signature bytes accordingly.

## Notes about the tests

* **SELF TEST DIAGNOSTICS**: Runs during initialization, checking the zero page, ROM, and RAM. If the ROM checksum is incorrect, the C1581 halts and repeatedly blinks the green LED twice.
* **Signature Test**: Executed via the `USER0` command `T` using the wedge `@U0>T`. In version `318045-02`, this test is broken due to wrong signature in the binary. When executed, it halts interrupts, calculates the ROM signature, and fails after approximately 11 seconds. The failure is indicated by the green LED blinking four times, stopping further execution until the drive is reset.

## Patching Steps

1. **Convert** `.bin` **to** `.hex`:
   
   First, convert the binary ROM file to a hexadecimal file using the `xxd` command on Linux
   ```
   xxd 1581-rom.318045-02.bin > 1581-rom.318045-02.modified.hex
   ```
   and open the `1581-rom.318045-02.modified.hex` file in preferred text editor.

2. **Re-enable SELF TEST** (for `318045-02`):

   Locate the line starting with 00002f80:. Ignore the string characters in the last column; the hexadecimal values are what matter. Modify the values as shown below. If you perform this step, you will also need to correct the checksum and signature bytes later (see the "Fixing Checksum and Signature" section).
   ```
   # From (318045-02):
   00002f80: 46c8 d0fb cad0 f669 ff85 47d0 00a9 0185  F......i..G.....
   
   # To (as in 318045-01):
   00002f80: 46c8 d0fb cad0 f669 ff85 47d0 3aa9 0185  F......i..G.:...
   ```

3. **Change Step Rates** for Type I Commands:

   Locate and modify the step rate instructions in the firmware. Look for the binary patterns `A9 08 8D`, `A9 18 8D`, etc., and update them to `A9 0A 8D`, `A9 1A 8D`, etc. These changes are found in lines starting with `00004300:`, `00004310:`, and `00004320:`.

   ```
   # Change from:
   00004300: 4e8d d701 a920 8dd8 0120 9fcb a908 8dda  N.... ... ......
   00004310: 01a9 188d db01 a928 8ddc 01a9 488d dd01  .......(....H...
   00004320: a968 8dde 01a9 888d df01 a9aa 8de0 01a9  .h..............
   
   # Change to:
   00004300: 4e8d d701 a920 8dd8 0120 9fcb a90a 8dda  N.... ... ......
   00004310: 01a9 1a8d db01 a92a 8ddc 01a9 4a8d dd01  .......*....J...
   00004320: a96a 8dde 01a9 888d df01 a9aa 8de0 01a9  .j..............
   ```

4. **Optionally Update** `dversion` **byte**:

   For the `318045-02` ROM, you can update the `dversion` field at the fourth byte. Change the value 01 (indicating -01) to 02 (indicating -02). This change is purely cosmetic and has no functional effect.
   ```
   # From:
   00000000: 4d19 cd01 a900 8535 2062 a8a5 5310 0929  M......5 b..S..)
   # To:
   00000000: 4d19 cd02 a900 8535 2062 a8a5 5310 0929  M......5 b..S..)
   ```

5. Fixing Checksum and Signature

   The first three bytes (signature and checksum) will need to be recalculated and corrected after making these changes. This step is detailed in the next section.

# Fixing Checksum and Signature

I created a Python script, `signature.py`, to calculate and update the checksum byte at position 3, along with the `signature_lo` and `signature_hi` bytes at positions 1 and 2 of the binary file.

## Steps

1. **Convert the Modified** `.hex` **File Back to Binary** Use the `xxd` command in Linux to convert the modified `.hex` file back into binary format `.bin`:
   ```
   xxd -r 1581-rom.318045-02.modified.hex > 1581-rom.318045-02.modified.bin
   ```

2. **Run the** `signature.py` **Python Script** to calculate, verify the checksum and signature. Initially, run it in dry-run mode (without the -w flag):

   ```
   ./signature.py -w 1581-rom.318045-02.modified.bin
   ```

3. **Review the Changes** After updating the checksum and signature, convert the updated `.bin` file back to a `.hex` file to review the changes:

   ```
   xxd 1581-rom.318045-02.modified.bin > 1581-rom.318045-02.modified.sigfixed.hex
   ```

4. **Verify the First Line** 
   Check the first line of the updated .hex file for the corrected first three bytes
   ```
   # Previous incorrect first three bytes in 1581-rom.318045-02.modified.hex
   00000000: 4d19 cd02 a900 8535 2062 a8a5 5310 0929  M......5 b..S..)
   
   # Corrected first three bytes (0xBC 0xE3 0x88) in 1581-rom.318045-02.modified.sigfixed.hex:
   00000000: bce3 8802 a900 8535 2062 a8a5 5310 0929  .......5 b..S..)
   ```
   That's it! The checksum and signature have been successfully updated.

# Burn the ROM to EPROM and Install in the C1581 with WD1772/VL1772

Burn the modified ROM file, `1581-rom.318045-02.modified.bin`, onto an `M27C256B` or simmilar EPROM chip using a programmer like the `TL866-II Pro`:
```
minipro -p "M27C256B@DIP28" -w 1581-rom.318045-02.modified.bin
```
Install the EPROM in the C1581 drive configured with either a WD1772 or VL1772 controller. With this setup, the C1581 now operates quietly! The `JU-353` drive mechanism also performs well at a 2ms step rate when the J1 jumper is closed in my case.

# Summary

After completing the modifications:
1. **Reduced Noise** and **Enhanced Reliability**
   * Drive noise has been significantly reduced, resulting in much quieter operation. 
   * Correct Step Rate The stepper motor now operates at the proper speed (3ms step rate), aligning with the JU-363 drive mechanism's specifications.
2. **Patched Firmware Compatibility**: The patched firmware functions reliably with WD1772 and VL1772 controllers.
3. **Functional Self-Tests**:
   * **SELF TEST DIAGNOSTICS**: Successfully re-enabled in the ROM. During initialization, the self-test verifies the zero page, ROM, and RAM, confirming the hardware's integrity. The C1581 now passes the self-test without errors.
   * **Signature Test**: Fixed to work properly with the wdge command (`@U0>T`). The test now calculates the ROM signature correctly without halting c1581. The green LED no longer indicates errors, and the drive operates as expected.

