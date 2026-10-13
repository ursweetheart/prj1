"""python ingest.py <dir> [max_images] -> process images and store in Postgres."""
import sys
from pipeline.processor import SpaceImageProcessor
from pipeline.store import save_records

if __name__ == "__main__":
    recs = SpaceImageProcessor().process_directory(sys.argv[1], max_images=int(sys.argv[2]) if len(sys.argv) > 2 else None)
    print(f"[+] saved {save_records(recs)} records")
