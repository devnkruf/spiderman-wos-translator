#!/usr/bin/env python3
import struct
import json
from pathlib import Path

STRING_MARKER = 0x15BADBAD  # The magic marker between length and text
LANG_STRING_START = 0x4F90  # Where strings begin in the LANG file
LANG_STRING_END = 0x4D310   # Where string section ends (length table starts)

class WoSLangEditor:
    def __init__(self, lang_data):
        """Initialize with LANG file data (raw bytes from the archive)."""
        self.data = bytearray(lang_data)
        self.strings = []
        self._parse()
    
    def _parse(self):
        """Parse ALL string entries from the LANG file.
        
        ALL entries use the same format:
        [4:LENGTH][4:MARKER][4:MARKER][N:TEXT][1:NULL][M:PADDING]
        
        Padding aligns entries to 4-byte boundaries.
        """
        # Verify magic
        magic = struct.unpack_from("<I", self.data, 0)[0]
        if magic != 0x12345678:
            raise ValueError(f"Invalid LANG magic: 0x{magic:08X}, expected 0x12345678")
        
        pos = LANG_STRING_START
        index = 0
        
        while pos < LANG_STRING_END - 12:
            # All entries: [length][marker][marker][text]
            length = struct.unpack_from("<I", self.data, pos)[0]
            marker1 = struct.unpack_from("<I", self.data, pos+4)[0]
            marker2 = struct.unpack_from("<I", self.data, pos+8)[0]
            
            if length > 0 and length < 5000 and marker1 == STRING_MARKER and marker2 == STRING_MARKER:
                # Valid entry
                text_start = pos + 12
                text_bytes = bytes(self.data[text_start:text_start + length])
                
                # Find next entry - look for next [length][marker] pattern
                # Don't blindly skip 0xA1 bytes!
                search_pos = text_start + length + 1  # After null byte
                
                # Align to 4-byte boundary
                if search_pos % 4 != 0:
                    search_pos = ((search_pos + 3) // 4) * 4
                
                # Now look for next valid entry
                next_pos = None
                while search_pos < LANG_STRING_END - 12:
                    peek_len = struct.unpack_from("<I", self.data, search_pos)[0]
                    peek_m1 = struct.unpack_from("<I", self.data, search_pos + 4)[0]
                    
                    if peek_len > 0 and peek_len < 5000 and peek_m1 == STRING_MARKER:
                        # Found next entry!
                        next_pos = search_pos
                        break
                    
                    # Move to next 4-byte aligned position
                    search_pos += 4
                
                if next_pos is None:
                    # No more entries, we're at the end
                    next_pos = LANG_STRING_END
                
                total_space = next_pos - pos
                
                self.strings.append({
                    'index': index,
                    'offset': pos,
                    'marker_offset': pos + 4,
                    'text_len': length,
                    'total_space': total_space,
                    'has_length_prefix': True,  # ALL entries have length prefix
                    'text_bytes': text_bytes,
                    'text': text_bytes.decode('utf-8', errors='replace')
                })
                
                index += 1
                pos = next_pos
                continue
            
            # If we get here, pattern didn't match
            # Move to next 4-byte aligned position and try again
            pos += 4
        
        self.string_section_end = LANG_STRING_END
        
        print(f"Parsed {len(self.strings)} strings")
        print(f"  All entries use UI format (with length prefix)")
        print(f"  String section ends at: 0x{self.string_section_end:X}")
    
    def export_strings(self, output_path, flexible=False):
        """Export strings to JSON."""
        entries = []
        
        for s in self.strings:
            entry = {
                'index': s['index'],
                'text': s['text'],
                'translated': s['text']
            }
            if flexible:
                entry['original_len'] = s['text_len']
                entry['max_len'] = s['total_space'] - 13  # 4+4+4+1 overhead
            entries.append(entry)
        
        output = {
            'metadata': {
                'total_strings': len(self.strings),
                'format_note': 'All entries use [LENGTH][MARKER][MARKER][TEXT][NULL][PADDING] format'
            },
            'strings': entries
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"Exported {len(entries)} strings to {output_path}")
    
    def import_strings_flexible(self, input_path, encoding='utf-8'):
        """Import with FLEXIBLE mode - fit text into existing slots."""
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        
        translations = data['strings'] if isinstance(data, dict) and 'strings' in data else data
        trans_map = {t['index']: t['translated'] for t in translations}
        
        modified = 0
        truncated = 0
        
        for s in self.strings:
            idx = s['index']
            if idx not in trans_map or trans_map[idx] == s['text']:
                continue
            
            new_text = trans_map[idx]
            try:
                new_bytes = new_text.encode(encoding)
            except UnicodeEncodeError:
                new_bytes = new_text.encode(encoding, errors='replace')
            
            # Calculate max space: total_space - 13 bytes overhead (4 len + 8 markers + 1 null)
            max_text_bytes = s['total_space'] - 13
            
            if len(new_bytes) > max_text_bytes:
                # Truncate
                new_bytes = new_bytes[:max_text_bytes]
                truncated += 1
            
            # Update length field
            struct.pack_into("<I", self.data, s['offset'], len(new_bytes))
            
            # Update text
            str_start = s['offset'] + 12  # After length + 2 markers
            self.data[str_start:str_start + len(new_bytes)] = new_bytes
            
            # Null terminator
            pos = str_start + len(new_bytes)
            self.data[pos] = 0x00
            pos += 1
            
            # Fill rest with padding
            entry_end = s['offset'] + s['total_space']
            while pos < entry_end:
                self.data[pos] = 0xA1
                pos += 1
            
            modified += 1
        
        print(f"Modified {modified} strings ({truncated} truncated)")
        return bytes(self.data)
    
    def import_strings_expanded(self, input_path, encoding='utf-8'):
        """Import with EXPANDED mode - rebuild entire string section.
        
        ALL entries use the same format:
        [4:LENGTH][4:MARKER][4:MARKER][N:TEXT][1:NULL][M:PADDING]
        
        This mode redistributes padding to accommodate longer translations.
        """
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        
        translations = data['strings'] if isinstance(data, dict) and 'strings' in data else data
        trans_map = {t['index']: t['translated'] for t in translations}
        
        if not self.strings:
            raise ValueError("No strings parsed!")
        
        # String section is from first string to length table
        first_offset = LANG_STRING_START
        string_section_size = LANG_STRING_END - first_offset
        
        print(f"String section: 0x{first_offset:X} - 0x{LANG_STRING_END:X}")
        print(f"Available for strings: {string_section_size:,} bytes")
        
        # Build entries with translated text
        entries = []
        total_text_bytes = 0
        
        for s in self.strings:
            idx = s['index']
            text = trans_map.get(idx, s['text'])
            
            try:
                text_bytes = text.encode(encoding)
            except UnicodeEncodeError:
                text_bytes = text.encode(encoding, errors='replace')
            
            entries.append({
                'index': idx,
                'text_bytes': text_bytes
            })
            total_text_bytes += len(text_bytes)
        
        # Calculate minimum space needed
        # Each entry: 4 (length) + 8 (markers) + text + 1 (null) = 13 + text
        # Plus padding to align to 4 bytes
        num_entries = len(entries)
        base_overhead = num_entries * 13  # length + markers + null
        
        # Calculate actual space needed with alignment
        min_space_needed = 0
        for e in entries:
            entry_size = 13 + len(e['text_bytes'])
            aligned_size = ((entry_size + 3) // 4) * 4
            min_space_needed += aligned_size
        
        print(f"Entries: {num_entries}")
        print(f"Total text: {total_text_bytes:,} bytes")
        print(f"Minimum needed (with alignment): {min_space_needed:,} bytes")
        
        if min_space_needed > string_section_size:
            diff = min_space_needed - string_section_size
            print(f"ERROR: Need {diff:,} more bytes!")
            print(f"Total translations are too long. Need to trim some strings.")
            return None
        
        extra_space = string_section_size - min_space_needed
        print(f"Extra space for padding: {extra_space:,} bytes")
        
        # Build new string section
        new_data = bytearray()
        new_lengths = []
        
        for entry in entries:
            text_bytes = entry['text_bytes']
            
            # Build entry: [length][marker][marker][text][null]
            entry_data = bytearray()
            entry_data.extend(struct.pack("<I", len(text_bytes)))  # Length
            entry_data.extend(struct.pack("<I", STRING_MARKER))    # Marker 1
            entry_data.extend(struct.pack("<I", STRING_MARKER))    # Marker 2
            entry_data.extend(text_bytes)                          # Text
            entry_data.append(0x00)                                # Null
            
            # Pad to 4-byte boundary
            base_size = len(entry_data)
            aligned_size = ((base_size + 3) // 4) * 4
            padding_needed = aligned_size - base_size
            entry_data.extend(b'\xA1' * padding_needed)
            
            new_data.extend(entry_data)
            new_lengths.append(len(text_bytes))
        
        # Fill remaining space with padding
        while len(new_data) < string_section_size:
            new_data.append(0xA1)
        
        # Truncate if somehow too long
        if len(new_data) > string_section_size:
            print(f"WARNING: Generated {len(new_data)} bytes, truncating to {string_section_size}")
            new_data = new_data[:string_section_size]
        
        print(f"Generated string section: {len(new_data)} bytes")
        
        # Replace string section
        self.data[first_offset:first_offset + string_section_size] = new_data
        
        # Update the length table
        length_table_offset = LANG_STRING_END
        print(f"Updating length table at 0x{length_table_offset:X} with {len(new_lengths)} entries...")
        
        for i, new_len in enumerate(new_lengths):
            table_entry_offset = length_table_offset + 4 + i * 4
            struct.pack_into("<I", self.data, table_entry_offset, new_len)
        
        print(f"Successfully rebuilt string section with {num_entries} entries")
        
        return bytes(self.data)


def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python wos_lang_editor_v3.py <command> <archive_path> [options]")
        print()
        print("Commands:")
        print("  extract <archive> <output.json>     - Extract strings to JSON")
        print("  import_flexible <archive> <input.json> <output>  - Import (fit in slots)")
        print("  import_expanded <archive> <input.json> <output>  - Import (rebuild section)")
        print()
        print("Archive is GLOBALTEXT_ENGLISH file (not .PCPACK)")
        return
    
    command = sys.argv[1]
    archive_path = sys.argv[2]
    
    # Read archive
    print(f"Reading {archive_path}...")
    with open(archive_path, 'rb') as f:
        archive_data = f.read()
    
    # LANG file is at offset 0x7FB50, size 336504 bytes
    LANG_OFFSET = 0x7FB50
    LANG_SIZE = 336504
    
    lang_data = archive_data[LANG_OFFSET:LANG_OFFSET + LANG_SIZE]
    print(f"Extracted LANG file: {len(lang_data)} bytes from offset 0x{LANG_OFFSET:X}")
    
    editor = WoSLangEditor(lang_data)
    
    if command == 'extract':
        output_path = sys.argv[3] if len(sys.argv) > 3 else 'strings_v3.json'
        editor.export_strings(output_path, flexible=True)
    
    elif command == 'import_flexible':
        input_json = sys.argv[3]
        output_path = sys.argv[4]
        
        new_lang = editor.import_strings_flexible(input_json)
        if new_lang:
            # Rebuild archive
            new_archive = bytearray(archive_data)
            new_archive[LANG_OFFSET:LANG_OFFSET + LANG_SIZE] = new_lang
            
            with open(output_path, 'wb') as f:
                f.write(new_archive)
            print(f"Saved to {output_path}")
    
    elif command == 'import_expanded':
        input_json = sys.argv[3]
        output_path = sys.argv[4]
        encoding = sys.argv[5] if len(sys.argv) > 5 else 'cp1252'
        
        new_lang = editor.import_strings_expanded(input_json, encoding=encoding)
        if new_lang:
            # Rebuild archive
            new_archive = bytearray(archive_data)
            new_archive[LANG_OFFSET:LANG_OFFSET + LANG_SIZE] = new_lang
            
            with open(output_path, 'wb') as f:
                f.write(new_archive)
            print(f"Saved to {output_path}")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
