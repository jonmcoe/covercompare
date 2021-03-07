from PIL import Image


def combine(path1, path2, output_path):
    img1 = Image.open(path1)
    img2 = Image.open(path2)
    shorter = min(img1, img2, key=lambda x: x.size[1])
    taller = max(img1, img2, key=lambda x: x.size[1])
    taller_resized = taller.resize(shorter.size)
    output_img = Image.new('RGB', (2 * shorter.size[0], shorter.size[1]), (250, 250, 250))
    if img1.size[1] < img2.size[1]:
        left, right = shorter, taller_resized
    else:
        left, right = taller_resized, shorter
    output_img.paste(left, (0,0))
    output_img.paste(right, (shorter.size[0], 0))
    output_img.save(output_path, 'JPEG')
    return output_path