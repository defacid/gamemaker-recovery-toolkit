using System;
using System.IO;
using UndertaleModLib.Util;

EnsureDataLoaded();

string outputRoot = Environment.GetEnvironmentVariable("DEFACID_BACKGROUNDS_OUT");
if (String.IsNullOrWhiteSpace(outputRoot))
    throw new Exception("DEFACID_BACKGROUNDS_OUT must name an output directory.");

Directory.CreateDirectory(outputRoot);
using (TextureWorker worker = new())
{
    foreach (var background in Data.Backgrounds)
    {
        if (background?.Texture is null)
            continue;
        string name = background.Name?.Content ?? "unnamed";
        worker.ExportAsPNG(background.Texture,
            Paths.JoinVerifyWithinDirectory(outputRoot, $"{name}.png"));
        Console.WriteLine($"Exported background: {name}");
    }
}
