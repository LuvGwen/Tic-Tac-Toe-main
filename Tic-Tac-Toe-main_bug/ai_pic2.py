import requests

prompt = "a cat is making a cake in the kitchen"

url = f"https://image.pollinations.ai/prompt/{prompt}"

img = requests.get(url).content

with open("cat.png", "wb") as f:

    f.write(img)