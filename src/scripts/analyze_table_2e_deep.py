import sys
import os
import struct

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.importer.pdb_importer import DeviceSqlImporter

def analyze_table_2e_structure():
    """
    Deep analysis of Table 0x2E to find pattern between dirty and clean names.
    Generates a detailed report for pattern detection.
    """
    path = "/media/esfingex/IVIR_R1/PIONEER/Rekordbox/export.pdb"
    
    importer = DeviceSqlImporter()
    if not importer.open(path):
        print("Failed to open PDB")
        return
    
    table_idx = importer._find_table_by_type(0x2E)
    if table_idx == 0:
        print("Table 0x2E not found")
        return
    
    print("="*80)
    print("TABLE 0x2E STRUCTURE ANALYSIS")
    print("="*80)
    
    page_data = importer.read_page(table_idx)
    if not page_data:
        return
    
    num_rows = struct.unpack_from('<H', page_data, 26)[0] & 0x1FFF
    print(f"\nTotal rows in first page: {num_rows}")
    print(f"\nAnalyzing first 20 rows in detail...\n")
    
    for i in range(min(20, num_rows)):
        ofs_pos = 4096 - 6 - (2*i)
        row_offset = struct.unpack_from('<H', page_data, ofs_pos)[0]
        
        if row_offset >= 4096 - 100:
            continue
            
        print(f"\n{'='*80}")
        print(f"ROW {i} - Offset: {row_offset} (0x{row_offset:X})")
        print(f"{'='*80}")
        
        # Read 200 bytes from row start
        row_data = page_data[row_offset:min(row_offset+200, 4096)]
        
        # 1. Hex dump first 100 bytes
        print("\nHEX DUMP (first 100 bytes):")
        for j in range(0, min(100, len(row_data)), 16):
            chunk = row_data[j:j+16]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(f"  {j:04X}: {hex_str:<48} {ascii_str}")
        
        # 2. Try to parse as structured data
        print("\nSTRUCTURED DATA INTERPRETATION:")
        try:
            # Common PDB row structure: ID at offset 0, various fields
            if len(row_data) >= 24:
                id_field = struct.unpack_from('<I', row_data, 0)[0]
                field_4 = struct.unpack_from('<I', row_data, 4)[0]
                field_8 = struct.unpack_from('<I', row_data, 8)[0]
                field_12 = struct.unpack_from('<I', row_data, 12)[0]
                field_16 = struct.unpack_from('<I', row_data, 16)[0]
                field_20 = struct.unpack_from('<I', row_data, 20)[0]
                
                print(f"  Offset 0  (ID?):     {id_field} (0x{id_field:08X})")
                print(f"  Offset 4:            {field_4} (0x{field_4:08X})")
                print(f"  Offset 8:            {field_8} (0x{field_8:08X})")
                print(f"  Offset 12:           {field_12} (0x{field_12:08X})")
                print(f"  Offset 16:           {field_16} (0x{field_16:08X})")
                print(f"  Offset 20:           {field_20} (0x{field_20:08X})")
        except:
            pass
        
        # 3. Extract all readable strings
        print("\nEXTRACTED STRINGS:")
        import re
        pattern = re.compile(b'[ -~]{3,64}')
        for match in pattern.finditer(row_data):
            text = match.group().decode('utf-8', errors='ignore')
            offset_in_row = match.start()
            print(f"  @{offset_in_row:3d}: '{text}'")
    
    importer.close()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nLook for patterns like:")
    print("- Two string fields (one dirty, one clean)")
    print("- A flag/byte that indicates which name to use")
    print("- Consistent offset positions for clean vs dirty names")
    print("- Length prefixes before strings")

if __name__ == "__main__":
    analyze_table_2e_structure()
