from pathlib import Path
from time import strftime
from urllib.parse import quote
from urllib.request import Request, urlopen


def generate_ai_image(prompt, output_dir):
    clean_prompt = prompt.strip()
    if not clean_prompt:
        raise ValueError("Prompt cannot be empty.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    encoded_prompt = quote(clean_prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        "?width=512&height=512&nologo=true"
    )

    request = Request(url, headers={"User-Agent": "ICDS-Chat-TicTacToe/1.0"})

    with urlopen(request, timeout=45) as response:
        image_bytes = response.read()
        content_type = response.headers.get("Content-Type", "").lower()

    if "png" in content_type:
        suffix = ".png"
    elif "jpeg" in content_type or "jpg" in content_type:
        suffix = ".jpg"
    else:
        suffix = ".png"

    filename = "ai_image_" + strftime("%Y%m%d_%H%M%S") + suffix
    file_path = output_path / filename
    file_path.write_bytes(image_bytes)

    return file_path
