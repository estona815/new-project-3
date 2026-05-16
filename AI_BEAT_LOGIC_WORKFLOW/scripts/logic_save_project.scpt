-- Best-effort save helper.
-- Logic Pro does not expose full project save control through plain AppleScript.
on run argv
	if (count of argv) < 1 then error "missing project path"
	tell application "Logic Pro"
		activate
	end tell
	return "Manual save may be required: " & (item 1 of argv)
end run

