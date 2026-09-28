using System;
using System.IO;
using UndertaleModLib.Models;

EnsureDataLoaded();

string outputDir = Environment.GetEnvironmentVariable("DEFACID_AUDIO_OUT");
if (String.IsNullOrWhiteSpace(outputDir))
    throw new Exception("DEFACID_AUDIO_OUT must name the output directory.");

Directory.CreateDirectory(outputDir);

foreach (UndertaleSound sound in Data.Sounds)
{
    if (sound == null)
        continue;

    bool compressed = sound.Flags.HasFlag(UndertaleSound.AudioEntryFlags.IsCompressed);
    bool embedded = sound.Flags.HasFlag(UndertaleSound.AudioEntryFlags.IsEmbedded);
    string extension = (embedded && !compressed) ? ".wav" : ".ogg";

    if (sound.AudioFile != null)
    {
        string path = Path.Combine(outputDir, sound.Name.Content + extension);
        File.WriteAllBytes(path, sound.AudioFile.Data);
        Console.WriteLine($"Wrote {path}");
    }
    else
    {
        Console.WriteLine($"Skipped non-embedded sound {sound.Name.Content} ({sound.File?.Content})");
    }
}
