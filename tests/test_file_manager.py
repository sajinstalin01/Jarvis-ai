import tempfile, unittest, zipfile
from pathlib import Path
from features.file_manager import FileManager

class FileManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.fm=FileManager()
    def tearDown(self): self.temp.cleanup()
    def test_create_and_search(self):
        folder=self.root/"My Documents"
        self.assertIn("Created folder",self.fm.dispatch(f'fm create folder "{folder}"'))
        note=folder/"meeting-notes.txt"
        self.assertIn("Created file",self.fm.dispatch(f'fm create file "{note}"'))
        note.write_text("JARVIS scheduling notes",encoding="utf-8")
        self.assertIn("meeting-notes.txt",self.fm.dispatch(f'fm search "{folder}" :: *.txt'))
        self.assertIn("meeting-notes.txt",self.fm.dispatch(f'fm search "{folder}" :: content:scheduling'))
    def test_copy_move_rename(self):
        src=self.root/"original.txt"; src.write_text("hello")
        cp=self.root/"copy.txt"; self.assertIn("Copy complete",self.fm.dispatch(f'fm copy "{src}" :: "{cp}"'))
        mv=self.root/"moved.txt"; self.assertIn("Move complete",self.fm.dispatch(f'fm move "{cp}" :: "{mv}"'))
        rn=self.root/"renamed.txt"; self.assertIn("Rename complete",self.fm.dispatch(f'fm rename "{mv}" :: "{rn}"'))
        self.assertTrue(rn.exists())
    def test_delete_confirmation(self):
        p=self.root/"remove me.txt"; p.write_text("safe")
        self.assertIn("CONFIRMATION REQUIRED",self.fm.dispatch(f'fm delete "{p}"')); self.assertTrue(p.exists())
        self.assertIn("Deleted",self.fm.dispatch(f'fm delete confirm "{p}"')); self.assertFalse(p.exists())
    def test_organize_confirmation(self):
        (self.root/"one.txt").write_text("1"); (self.root/"two.py").write_text("2")
        self.assertIn("ORGANIZE PREVIEW",self.fm.dispatch(f'fm organize "{self.root}" :: type'))
        self.assertTrue((self.root/"one.txt").exists())
        self.assertIn("Organization complete",self.fm.dispatch("fm organize confirm"))
        self.assertTrue((self.root/"txt"/"one.txt").exists()); self.assertTrue((self.root/"py"/"two.py").exists())
    def test_zip_unzip(self):
        src=self.root/"source"; src.mkdir(); (src/"hello.txt").write_text("hello")
        archive=self.root/"source.zip"; self.assertIn("Archive created",self.fm.dispatch(f'fm zip "{src}" :: "{archive}"'))
        dest=self.root/"extracted"; self.assertIn("Extracted",self.fm.dispatch(f'fm unzip "{archive}" :: "{dest}"'))
        self.assertTrue((dest/"source"/"hello.txt").exists())
    def test_zip_slip_blocked(self):
        archive=self.root/"evil.zip"
        with zipfile.ZipFile(archive,"w") as z: z.writestr("../escape.txt","bad")
        dest=self.root/"extract"
        self.assertIn("unsafe path",self.fm.dispatch(f'fm unzip "{archive}" :: "{dest}"'))
        self.assertFalse((self.root/"escape.txt").exists())
    def test_dirs_and_hub_integration(self):
        self.assertIn("Downloads",self.fm.dispatch("fm dirs"))
        from features.hub import FeatureHub
        hub=FeatureHub(self.root)
        target=self.root/"hub.txt"
        self.assertIn("Created file",hub.dispatch(f'fm create file "{target}"'))

if __name__ == "__main__": unittest.main()
