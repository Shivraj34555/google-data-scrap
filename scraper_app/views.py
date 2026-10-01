import os
import uuid
import asyncio
import threading
import re
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

# Import the existing scraper module from the project root
from scraper import run_scraper

# In-memory dictionary to track async scraper tasks
# Format: { task_id: {"status": "running" | "done" | "error", "file_path": str, "error": str, "message": str} }
tasks = {}

def index(request):
    """Renders the main dashboard index page."""
    return render(request, 'index.html')

@csrf_exempt
def scrape_data(request):
    """
    POST endpoint to trigger background Google Maps scraping.
    Spawns a background thread to handle the async playwright scraper.
    """
    if request.method == 'POST':
        city = request.POST.get('city', '')
        keyword = request.POST.get('keyword', '')
        
        if not city or not keyword:
            return JsonResponse({"error": "City and keyword parameters are required."}, status=400)
            
        task_id = str(uuid.uuid4())
        tasks[task_id] = {"status": "running", "logs": []}
        
        # Start the background scraping process in a separate thread
        # this ensures the main Django server is not blocked.
        thread = threading.Thread(target=start_scraper_thread, args=(task_id, city, keyword))
        thread.daemon = True
        thread.start()
        
        return JsonResponse({"task_id": task_id})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def get_status(request, task_id):
    """GET endpoint to fetch the logs and current status of a task."""
    if task_id not in tasks:
        return JsonResponse({"error": "Task not found"}, status=404)
    return JsonResponse(tasks[task_id])

def download_file(request, task_id):
    """GET endpoint to download the generated Excel sheet for a finished task."""
    task = tasks.get(task_id)
    if not task or task["status"] != "done":
        return JsonResponse({"error": "File not ready or task failed"}, status=400)
    
    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return JsonResponse({"error": "Generated file not found on disk"}, status=404)
        
    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def start_scraper_thread(task_id, city_str, keyword_str):
    """Target function for background thread to run the async Playwright scraper."""
    # Create a new asyncio event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_scraper_task(task_id, city_str, keyword_str))
    finally:
        loop.close()

async def run_scraper_task(task_id: str, city_str: str, keyword_str: str):
    """Asynchronous wrapper that invokes the playwright scraper and handles progress logging."""
    try:
        def append_log(msg):
            if task_id in tasks:
                tasks[task_id]["logs"].append(msg)

        # Split city & categories inputs by comma/newline
        cities = [c.strip() for c in re.split(r'[,\n]+', city_str) if c.strip()]
        categories = [k.strip() for k in re.split(r'[,\n]+', keyword_str) if k.strip()]
        
        filepath, total_records = await run_scraper(cities, categories, log_callback=append_log)
        
        if filepath and os.path.exists(filepath):
            tasks[task_id] = {
                "status": "done",
                "file_path": filepath,
                "message": f"Successfully found and extracted {total_records} records to Excel."
            }
        else:
            tasks[task_id] = {
                "status": "error",
                "error": "No data extracted or file not saved."
            }
    except Exception as e:
        tasks[task_id] = {
            "status": "error",
            "error": str(e)
        }
