import argparse
import json
import shutil
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
            for relative_path in generator.DEFAULT_FILES:
                self.assertEqual(
                    (project / (relative_path if relative_path.endswith('.md')
                                else 'Client WebApp.code-workspace')).read_bytes(),
                    (generator.TEMPLATE_DIR / relative_path).read_bytes())
            self.assertFalse((project / 'workspace.code-workspace').exists())

    def test_standalone_script_creates_all_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'create_workspace.py'
            shutil.copyfile(generator.__file__, script)
            result = subprocess.run([
                sys.executable, str(script), '--ProjectName', 'Standalone',
                '--ParentDir', temporary,
            ], cwd=temporary, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            project = Path(temporary) / 'Standalone'
            for relative_path, content in generator.DEFAULT_FILES.items():
                target = project / (relative_path if relative_path.endswith('.md')
                                    else 'Standalone.code-workspace')
                self.assertEqual(target.read_text(encoding='utf-8'), content)
            for directory in generator.EMPTY_DIRS:
                self.assertTrue((project / directory).is_dir())

    def test_partial_template_preserves_custom_content_and_fills_missing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            template = Path(temporary) / 'template'
            workspace = template / 'AI-Workspace'
            workspace.mkdir(parents=True)
            (workspace / '00 Scope.md').write_text('# Custom scope\n')
            with patch.object(generator, 'TEMPLATE_DIR', template):
                project = generator.create_workspace('Client', temporary)
            self.assertEqual((project / 'AI-Workspace/00 Scope.md').read_text(),
                             '# Custom scope\n')
            for relative_path, content in generator.DEFAULT_FILES.items():
                if relative_path in ('AI-Workspace/00 Scope.md', 'workspace.code-workspace'):
                    continue
                self.assertEqual((project / relative_path).read_text(encoding='utf-8'), content)
            self.assertEqual(json.loads((project / 'Client.code-workspace').read_text())
                             ['folders'], [{'path': '.'}])

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
