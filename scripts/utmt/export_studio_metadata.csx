using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

EnsureDataLoaded();

string outputPath = Environment.GetEnvironmentVariable("DEFACID_METADATA_OUT");
if (String.IsNullOrWhiteSpace(outputPath))
    throw new Exception("DEFACID_METADATA_OUT must name the output JSON file.");

string NameOf(object resource)
{
    if (resource == null)
        return null;
    object value = resource;
    var resourceProperty = value.GetType().GetProperty("Resource");
    if (resourceProperty != null)
        value = resourceProperty.GetValue(value);
    if (value == null)
        return null;
    var nameProperty = value.GetType().GetProperty("Name");
    object name = nameProperty?.GetValue(value);
    if (name == null)
        return null;
    var contentProperty = name.GetType().GetProperty("Content");
    return contentProperty?.GetValue(name)?.ToString();
}

var root = new JObject
{
    ["project"] = Data.GeneralInfo.Name?.Content,
    ["bytecodeVersion"] = Data.GeneralInfo.BytecodeVersion,
    ["interpolatePixels"] = Data.GeneralInfo.Info.ToString().Contains("InterpolatePixels")
};

var sprites = new JArray();
foreach (var sprite in Data.Sprites)
{
    if (sprite == null)
        continue;
    sprites.Add(new JObject
    {
        ["name"] = sprite.Name?.Content,
        ["width"] = sprite.Width,
        ["height"] = sprite.Height,
        ["originX"] = sprite.OriginX,
        ["originY"] = sprite.OriginY,
        ["bboxLeft"] = sprite.MarginLeft,
        ["bboxRight"] = sprite.MarginRight,
        ["bboxTop"] = sprite.MarginTop,
        ["bboxBottom"] = sprite.MarginBottom,
        ["bboxMode"] = Convert.ToInt32(sprite.BBoxMode),
        ["separateMasks"] = Convert.ToInt32(sprite.SepMasks),
        ["frameCount"] = sprite.Textures?.Count ?? 0,
        ["frames"] = sprite.Textures == null ? new JArray() : new JArray(sprite.Textures.Select(entry => entry?.Texture == null ? null : new JObject
        {
            ["targetX"] = entry.Texture.TargetX,
            ["targetY"] = entry.Texture.TargetY,
            ["targetWidth"] = entry.Texture.TargetWidth,
            ["targetHeight"] = entry.Texture.TargetHeight,
            ["boundingWidth"] = entry.Texture.BoundingWidth,
            ["boundingHeight"] = entry.Texture.BoundingHeight
        }))
    });
}
root["sprites"] = sprites;

var backgrounds = new JArray();
foreach (var background in Data.Backgrounds)
{
    if (background == null)
        continue;
    backgrounds.Add(new JObject { ["name"] = background.Name?.Content });
}
root["backgrounds"] = backgrounds;

var objects = new JArray();
foreach (var obj in Data.GameObjects)
{
    if (obj == null)
        continue;
    var events = new JArray();
    for (int eventType = 0; eventType < obj.Events.Count; eventType++)
    {
        foreach (var ev in obj.Events[eventType])
        {
            var actions = new JArray();
            foreach (var action in ev.Actions)
                actions.Add(NameOf(action.CodeId));
            events.Add(new JObject
            {
                ["eventType"] = eventType,
                ["eventSubtype"] = Convert.ToInt32(ev.EventSubtype),
                ["code"] = actions
            });
        }
    }
    objects.Add(new JObject
    {
        ["name"] = obj.Name?.Content,
        ["sprite"] = NameOf(obj.Sprite),
        ["mask"] = NameOf(obj.TextureMaskId),
        ["parent"] = NameOf(obj.ParentId),
        ["visible"] = obj.Visible,
        ["solid"] = obj.Solid,
        ["persistent"] = obj.Persistent,
        ["depth"] = obj.Depth,
        ["events"] = events
    });
}
root["objects"] = objects;

var rooms = new JArray();
foreach (var room in Data.Rooms)
{
    if (room == null)
        continue;
    var instances = new JArray();
    foreach (var instance in room.GameObjects)
    {
        instances.Add(new JObject
        {
            ["id"] = instance.InstanceID,
            ["object"] = NameOf(instance.ObjectDefinition),
            ["x"] = instance.X,
            ["y"] = instance.Y,
            ["scaleX"] = instance.ScaleX,
            ["scaleY"] = instance.ScaleY,
            ["rotation"] = instance.Rotation,
            ["imageSpeed"] = instance.ImageSpeed,
            ["imageIndex"] = instance.ImageIndex,
            ["creationCode"] = NameOf(instance.CreationCode)
        });
    }

    var views = new JArray();
    foreach (var view in room.Views)
    {
        views.Add(new JObject
        {
            ["enabled"] = view.Enabled,
            ["x"] = view.ViewX,
            ["y"] = view.ViewY,
            ["width"] = view.ViewWidth,
            ["height"] = view.ViewHeight,
            ["portX"] = view.PortX,
            ["portY"] = view.PortY,
            ["portWidth"] = view.PortWidth,
            ["portHeight"] = view.PortHeight,
            ["borderX"] = view.BorderX,
            ["borderY"] = view.BorderY,
            ["speedX"] = view.SpeedX,
            ["speedY"] = view.SpeedY,
            ["object"] = NameOf(view.ObjectId)
        });
    }

    var roomBackgrounds = new JArray();
    foreach (var background in room.Backgrounds)
    {
        roomBackgrounds.Add(new JObject
        {
            ["enabled"] = background.Enabled,
            ["foreground"] = background.Foreground,
            ["background"] = NameOf(background.BackgroundDefinition),
            ["x"] = background.X,
            ["y"] = background.Y,
            ["speedX"] = background.SpeedX,
            ["speedY"] = background.SpeedY,
            ["stretch"] = background.Stretch,
            ["tileX"] = background.TiledHorizontally,
            ["tileY"] = background.TiledVertically
        });
    }

    var tiles = new JArray();
    foreach (var tile in room.Tiles)
    {
        tiles.Add(new JObject
        {
            ["x"] = tile.X,
            ["y"] = tile.Y,
            ["background"] = NameOf(tile.BackgroundDefinition),
            ["sourceX"] = tile.SourceX,
            ["sourceY"] = tile.SourceY,
            ["width"] = tile.Width,
            ["height"] = tile.Height,
            ["depth"] = tile.TileDepth,
            ["scaleX"] = tile.ScaleX,
            ["scaleY"] = tile.ScaleY,
            ["id"] = tile.InstanceID
        });
    }

    rooms.Add(new JObject
    {
        ["name"] = room.Name?.Content,
        ["width"] = room.Width,
        ["height"] = room.Height,
        ["speed"] = room.Speed,
        ["persistent"] = room.Persistent,
        ["backgroundColor"] = room.BackgroundColor,
        ["drawBackgroundColor"] = room.DrawBackgroundColor,
        ["flags"] = Convert.ToUInt32(room.Flags),
        ["creationCode"] = NameOf(room.CreationCodeId),
        ["instances"] = instances,
        ["views"] = views,
        ["backgrounds"] = roomBackgrounds,
        ["tiles"] = tiles
    });
}
root["rooms"] = rooms;

var scripts = new JArray();
foreach (var script in Data.Scripts)
    if (script != null)
        scripts.Add(new JObject { ["name"] = script.Name?.Content, ["code"] = NameOf(script.Code) });
root["scripts"] = scripts;

var sounds = new JArray();
foreach (var sound in Data.Sounds)
{
    if (sound == null)
        continue;
    sounds.Add(new JObject
    {
        ["name"] = sound.Name?.Content,
        ["file"] = sound.File?.Content,
        ["type"] = sound.Type?.Content,
        ["volume"] = sound.Volume,
        ["pitch"] = sound.Pitch,
        ["audioId"] = sound.AudioID,
        ["groupId"] = sound.GroupID
    });
}
root["sounds"] = sounds;

var fonts = new JArray();
foreach (var font in Data.Fonts)
{
    if (font == null)
        continue;
    var glyphs = new JArray();
    foreach (var glyph in font.Glyphs)
    {
        glyphs.Add(new JObject
        {
            ["character"] = glyph.Character,
            ["x"] = glyph.SourceX,
            ["y"] = glyph.SourceY,
            ["w"] = glyph.SourceWidth,
            ["h"] = glyph.SourceHeight,
            ["shift"] = glyph.Shift,
            ["offset"] = glyph.Offset
        });
    }
    fonts.Add(new JObject
    {
        ["name"] = font.Name?.Content,
        ["displayName"] = font.DisplayName?.Content,
        ["size"] = font.EmSize,
        ["bold"] = font.Bold,
        ["italic"] = font.Italic,
        ["rangeStart"] = font.RangeStart,
        ["rangeEnd"] = font.RangeEnd,
        ["lineHeight"] = font.LineHeight,
        ["ascender"] = font.Ascender,
        ["ascenderOffset"] = font.AscenderOffset,
        ["glyphs"] = glyphs
    });
}
root["fonts"] = fonts;

Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)));
File.WriteAllText(outputPath, root.ToString(Formatting.Indented));
Console.WriteLine($"Wrote Studio metadata to {outputPath}");
