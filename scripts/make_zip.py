"""Write downloads/CardboardColin-beta.zip (fonts, CSS, licence, README)."""
import zipfile, os
os.makedirs("downloads", exist_ok=True)
out = "downloads/CardboardColin-beta.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root in ["fonts", "css"]:
        for d, _, fs in sorted(os.walk(root)):
            for f in sorted(fs):
                z.write(os.path.join(d, f), os.path.join("CardboardColin", d, f))
    for f in ["OFL.txt", "README.md"]:
        z.write(f, "CardboardColin/" + f)
print(out, os.path.getsize(out))
