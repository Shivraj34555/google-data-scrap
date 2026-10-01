import asyncio
import os
import argparse
from scraper import run_scraper

CATEGORIES = [
    "Salons & Beauty Parlours",
    "Gyms & Fitness Trainers",
    "Restaurants / Cafes",
    "Coaching Classes / Tuition Centers",
    "Clinics (Doctors / Dentists)"
]

def main():
    parser = argparse.ArgumentParser(description="Google Maps Scraper")
    parser.add_argument("--city", "-c", type=str, help="The city to search in (e.g., 'Pune')")
    parser.add_argument("--categories", "-k", type=str, help="Categories/Domains (e.g., 'Cafe, Clinics')")

    args = parser.parse_args()

    # Interactive mode if arguments are not provided
    city = args.city
    categories_input = args.categories

    if not city:
        city = input("Enter Cities (e.g., Pune, Mumbai): ").strip()
        if not city:
            print("City cannot be empty.")
            return

    if not categories_input:
        categories_input = input("Enter Categories (e.g., Cafe, Clinics): ").strip()
        if not categories_input:
            print("Categories cannot be empty.")
            return

    print(f"\nTarget(s): {categories_input} in {city}\n")
    print("Initializing browser and starting the extraction...\n")

    cities_list = [c.strip() for c in city.split(',') if c.strip()]
    categories_list = [k.strip() for k in categories_input.split(',') if k.strip()]

    # Run the playwright scraper
    try:
        filepath, count = asyncio.run(run_scraper(cities_list, categories_list))
        print(f"\nExtraction completed successfully! File saved: {filepath} with {count} records.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
