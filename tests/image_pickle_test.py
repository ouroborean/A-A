import dill as pickle

import PIL
from PIL import Image

def test_image_conversion():
    image = Image.open("test_image.png")

    image_pouch = {"mode": image.mode, "size": image.size, "pixels": image.tobytes()}

    msg = pickle.dumps(image_pouch)

    msg = list(msg)

    msg = bytes(msg)

    with open(f"test_image.dat", "wb") as f:
        f.write(msg)
    
    with open(f"test_image.dat", "rb") as f:
        code = f.read()
    
    msg = list(code)

    msg = bytes(msg)

    new_pouch = pickle.loads(msg)

    new_image = Image.frombytes(new_pouch["mode"], new_pouch["size"], new_pouch["pixels"])

    new_image.save("transferred_image.png")

