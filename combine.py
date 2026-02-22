from PIL import Image, ImageChops


def _trim_whitespace(img):
    bg = Image.new('RGB', img.size, (255, 255, 255))
    diff = ImageChops.difference(img.convert('RGB'), bg)
    diff = diff.point(lambda p: 0 if p < 10 else 255)
    bbox = diff.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def combine(paths, output_path, trim_flags=None):
    if trim_flags is None:
        trim_flags = [False] * len(paths)

    images = []
    for path, trim in zip(paths, trim_flags):
        img = Image.open(path).convert('RGB')
        if trim:
            img = _trim_whitespace(img)
        images.append(img)

    target_height = min(img.size[1] for img in images)

    resized = []
    for img in images:
        w, h = img.size
        new_w = round(w * target_height / h)
        resized.append(img.resize((new_w, target_height), Image.LANCZOS))

    total_width = sum(img.size[0] for img in resized)
    output_img = Image.new('RGB', (total_width, target_height), (250, 250, 250))

    x = 0
    for img in resized:
        output_img.paste(img, (x, 0))
        x += img.size[0]

    output_img.save(output_path, 'JPEG')
    return output_path
