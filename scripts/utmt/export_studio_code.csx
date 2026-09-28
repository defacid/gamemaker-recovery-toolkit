using System;
using System.IO;
using UndertaleModLib.Decompiler;

EnsureDataLoaded();
string outputRoot = Environment.GetEnvironmentVariable("DEFACID_CODE_OUT");
if (String.IsNullOrWhiteSpace(outputRoot))
    throw new Exception("DEFACID_CODE_OUT must name an output directory.");
Directory.CreateDirectory(outputRoot);
GlobalDecompileContext context = new(Data);
Underanalyzer.Decompiler.IDecompileSettings settings = Data.ToolInfo.DecompilerSettings;
foreach (var code in Data.Code)
{
    if (code?.Name?.Content is null || code.ParentEntry is not null)
        continue;
    string text = new Underanalyzer.Decompiler.DecompileContext(context, code, settings).DecompileToString();
    File.WriteAllText(Path.Combine(outputRoot, code.Name.Content + ".gml"), text);
    Console.WriteLine($"Exported code: {code.Name.Content}");
}
