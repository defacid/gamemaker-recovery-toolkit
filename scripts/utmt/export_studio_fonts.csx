using System;
using System.IO;
using UndertaleModLib.Util;

EnsureDataLoaded();

string outputDir = Environment.GetEnvironmentVariable("DEFACID_FONTS_OUT");
if (String.IsNullOrWhiteSpace(outputDir))
    throw new Exception("DEFACID_FONTS_OUT must name the output directory.");
Directory.CreateDirectory(outputDir);

using (TextureWorker worker = new TextureWorker())
{
    foreach (var font in Data.Fonts)
    {
        if (font?.Name?.Content == null || font.Texture == null)
            continue;
        string output = Path.Combine(outputDir, $"{font.Name.Content}.png");
        worker.ExportAsPNG(font.Texture, output, null, true);
        Console.WriteLine($"Wrote {output}");
    }
}
