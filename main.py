import os
from time import sleep
from src.email_fetcher.email_fetcher_api import gmail_fetch
from src.summarizer.summarizer import run_summarizer, save_script
from src.podcast_generator.podcast_generater import gen_podcast



def main():
    # test
    user_id = "me"
    query = '("job alert" OR "medium" OR "联合早报" OR "eCHO") newer_than:3d'
    print("Starting email fetching...")
    # Step 1: Fetch emails
    gmail_fetch(user_id, query)
    
    print("Emails fetched successfully!")
    
    print("\nStarting summarization...")
    # Step 2: Generate podcast script
    topic = "news, tech blogs, Job alerts"
    script = run_summarizer(topic)
    save_script(script)
    print("Podcast script generated successfully!")
    
    # Step 3: Generate audio
    print("\nStarting audio generation...")
    # Get current directory
    # current_dir = os.path.dirname(__file__)
    # Define output paths
    # script_path = os.path.join(current_dir, "temp", "podcast_script.txt")
    # output_path = os.path.join(current_dir, "temp", "podcast_output.wav")
    
    gen_podcast()


if __name__ == "__main__":
    main()