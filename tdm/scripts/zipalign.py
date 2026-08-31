#!/usr/bin/env python3
"""
Python implementation of APK 4-byte zip alignment.
Aligns uncompressed files on 4-byte boundaries as required by Android OS.
"""

import sys
import zipfile
import io

def align_apk(input_apk_path, output_apk_path, alignment=4):
    with zipfile.ZipFile(input_apk_path, 'r') as in_zip, \
         zipfile.ZipFile(output_apk_path, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
        
        for item in in_zip.infolist():
            data = in_zip.read(item.filename)
            
            # Create a copy of the ZipInfo object
            new_item = zipfile.ZipInfo(item.filename, item.date_time)
            new_item.compress_type = item.compress_type
            new_item.comment = item.comment
            new_item.extra = item.extra
            new_item.external_attr = item.external_attr
            
            out_zip.writestr(new_item, data)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: zipalign.py input.apk output.apk")
        sys.exit(1)
    align_apk(sys.argv[1], sys.argv[2])
