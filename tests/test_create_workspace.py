import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import create_workspace as generator


class WorkspaceTests(unittest.TestCase):
    def test_cli_from_another_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / 'parent with spaces' / 'nested'
            result = subprocess.run([
                sys.executable, str(Path(generator.__file__).resolve()),
                '--ProjectName', 'Client WebApp', '--ParentDir', str(parent)
            ], cwd=temporary, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            project = parent / 'Client WebApp'
            workspace = json.loads((project / 'Client WebApp.code-workspace').read_text())
            self.assertEqual(workspace['folders'], [{'path': '.'}])
            for directory in generator.EMPTY_DIRS:
                self.assertTrue((project / directory).is_dir())
                self.assertEqual(list((project / directory).iterdir()), [])
            self.assertEqual((project / 'AI-Workspace/AGENTS.md').read_bytes(),
                             (generator.TEMPLATE_DIR / 'AI-Workspace/AGENTS.md').read_bytes())
            self.assertFalse((project / 'workspace.code-workspace').exists())

    def test_existing_destination_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = generator.create_workspace('Client', temporary)
            evidence = project / 'AI-Workspace/SecretScrub/evidence.jsonl'
            evidence.write_text('preserve me')
            with self.assertRaises(FileExistsError):
                generator.create_workspace('Client', temporary)
            self.assertEqual(evidence.read_text(), 'preserve me')

    def test_portable_names(self):
        for name in ('', '.', '..', '../escape', 'a/b', 'a\\b', 'C:\\test',
                     'NUL', 'con.txt', 'COM1', 'LPT9.txt', 'bad?', 'bad:',
                     'trailing.', ' space', 'space ', 'a\n', 'COM¹'):
            with self.subTest(name=name), self.assertRaises(argparse.ArgumentTypeError):
                generator.project_name(name)
        self.assertEqual(generator.project_name('Client WebApp-01'), 'Client WebApp-01')

    def test_copy_failure_removes_only_new_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            sibling = Path(temporary) / 'keep.txt'
            sibling.write_text('keep')
            with patch.object(generator.shutil, 'copytree', side_effect=OSError('copy failed')):
                with self.assertRaises(OSError):
                    generator.create_workspace('Client', temporary)
            self.assertFalse((Path(temporary) / 'Client').exists())
            self.assertEqual(sibling.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
