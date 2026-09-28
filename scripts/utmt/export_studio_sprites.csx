using System;
using System.IO;
using UndertaleModLib.Util;

EnsureDataLoaded();

string outputDir = Environment.GetEnvironmentVariable("DEFACID_SPRITES_OUT");
if (String.IsNullOrWhiteSpace(outputDir))
    throw new Exception("DEFACID_SPRITES_OUT must name the output directory.");
Directory.CreateDirectory(outputDir);

using (TextureWorker worker = new TextureWorker())
{
    foreach (var sprite in Data.Sprites)
    {
        if (sprite?.Name?.Content == null || sprite.Textures == null)
            continue;
        for (int index = 0; index < sprite.Textures.Count; index++)
        {
            var item = sprite.Textures[index]?.Texture;
            if (item == null)
                continue;
            string output = Path.Combine(outputDir, $"{sprite.Name.Content}_{index}.png");
            // Preserve TargetX/TargetY placement inside the original sprite
            // canvas. Unpadded exports move trimmed texture-page pixels to
            // (0,0), breaking authored origins, flipping, shadows, and masks.
            worker.ExportAsPNG(item, output, null, true);
            Console.WriteLine($"Wrote {output}");
        }
    }
}
