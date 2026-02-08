#!/usr/bin/env python3
from pathlib import Path
import os, io, argparse, subprocess, json
import exiftool
import geobuf
from rich.progress import Progress

"""
Creates geojson, geobuf, and pmtiles.
"""

def find_mp4_files(directory_path):
    """
    Finds all .mp4 files recursively within the specified directory.

    Args:
        directory_path (str or Path): The root directory to start searching from.

    Returns:
        list: A list of Path objects for all found .mp4 files.
    """
    # Create a Path object from the input string
    root_dir = Path(directory_path)
    
    # Use rglob (recursive glob) to find all files matching the pattern "*.mp4"
    # and convert the generator object to a list
    mp4_files = list(root_dir.rglob("*F.MP4"))
    mp4_files += list(root_dir.rglob("*F.MOV"))
    
    return mp4_files

def main():
    # 1. Initialize the parser
    parser = argparse.ArgumentParser(
        description="Creates geojson, geobuf, and pmtiles."
    )

    # 2. Define the -o argument (Single value)
    parser.add_argument(
        '-o', 
        '--output', 
        required=True, 
        help="Path to the output file"
    )

    # 3. Define the -i argument (List of values)
    # nargs='+' means 1 or more arguments are required
    parser.add_argument(
        '-i', 
        '--input', 
        nargs='+', 
        required=True, 
        help="List of input folders (space-separated)"
    )

    # 4. Parse the arguments
    args = parser.parse_args()

    # Accessing the values
    output_path = args.output
    if os.path.splitext(output_path) != ".pmtiles":
        output_path += ".pmtiles"
    print(f"Output destination: {output_path}")
    print(f"Number of input folders: {len(args.input)}")

    geobuf_files = []

    # Example usage:
    exif = exiftool.ExifToolHelper()

    for folder in args.input:
        files_found = find_mp4_files(folder) 
        sorted_files = sorted(files_found)
        # Generate GeoJSON
        with Progress(speed_estimate_period=720) as pb:
            t1 = pb.add_task(f'Progress', total=len(sorted_files))
            basename = os.path.basename(folder)
            with open(f"{basename}.geojson", "w+") as f:
                f.write("{\"type\": \"Feature\",\"geometry\": {\"type\":\"LineString\",\"coordinates\": [")
                text_buffer = io.StringIO()
                finished_count = 0
                for p in sorted_files:
                    p_str = p.as_posix()
                    result = exif.execute("-p", "./coor.fmt", "-ee", p_str)
                    text_buffer.write(result)
                    finished_count += 1
                    pb.update(task_id=t1, completed=finished_count)
                f.write(text_buffer.getvalue()[0:-1])
                f.write("]}}")

            with open(f"{basename}.geojson", "r") as f:
                geobuf_file = geobuf.encode(json.load(f))
                with open(f"{basename}.geobuf", "wb") as g:
                    g.write(geobuf_file)
                    geobuf_files.append(f"{basename}.geobuf")
                
    command = [
        "tippecanoe",
        "-o", output_path,
        "-zg",
        "--force"
    ] + geobuf_files

    print(f"Creating: {output_path}")

    try:
        subprocess.run(command, check=True)
        print(f"Successfully created {output_path}\n")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {output_path}: {e}\n")
    except FileNotFoundError:
        print("Error: Tippecanoe is not installed or not in your PATH.\n")
        

if __name__ == "__main__":
    main()