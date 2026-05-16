-- Best-effort import helper.
-- AppleScript support in Logic Pro is limited; this script prepares Finder selection
-- so the user can import manually if direct UI scripting is blocked.
on run argv
	if (count of argv) < 1 then error "missing audio path"
	set audioPath to POSIX file (item 1 of argv)
	tell application "Finder"
		reveal audioPath
	end tell
	tell application "Logic Pro"
		activate
	end tell
end run

