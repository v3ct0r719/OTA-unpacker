# OTA-unpacker
A tool for unpacking Android OTA update files (Both full and incremental updates ).

## Usage

To see usage just run :

```bash
./unpacker.py -h
```

If it is a full update, then run: 

```bash
./unpacker.py ota_update.zip
```

In case of an incremental update, then run:

```bash
./unpacker.py -i -o ota_update.zip incremental_ota_update.zip
```

Instead of giving there zip's you can also give their corresponding `payload.bin` as the argument.

Here is how the output is during extraction
```
Extracting payload.bin from zip
+-----------+----------+
|  Images   |   Size   |
+===========+==========+
| xbl       | 2.6MiB   |
+-----------+----------+
| rpm       | 232.0KiB |
+-----------+----------+
| tz        | 1.9MiB   |
+-----------+----------+
| hyp       | 264.0KiB |
+-----------+----------+
| pmic      | 52.0KiB  |
+-----------+----------+
| modem     | 23.5MiB  |
+-----------+----------+
| abl       | 212.0KiB |
+-----------+----------+
| boot      | 25.3MiB  |
+-----------+----------+
| keymaster | 372.0KiB |
+-----------+----------+
| cmnlib    | 220.0KiB |
+-----------+----------+
| cmnlib64  | 288.0KiB |
+-----------+----------+
| system    | 2.5GiB   |
+-----------+----------+
| devcfg    | 60.0KiB  |
+-----------+----------+
| ovrtz     | 120.0KiB |
+-----------+----------+
Extracting partition : xbl  .....done
Extracting partition : rpm  ....done
Extracting partition : tz  ....done
Extracting partition : hyp  ....done
Extracting partition : pmic  ....done
Extracting partition : modem  ...............done
Extracting partition : abl  ....done
Extracting partition : boot  ................done
Extracting partition : keymaster  ....done
Extracting partition : cmnlib  ....done
Extracting partition : cmnlib64  ....done
Extracting partition : system .......................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................done
Extracting partition : devcfg  ....done
Extracting partition : ovrtz  ....done
```
The Partitions are extracted  in `output/`



