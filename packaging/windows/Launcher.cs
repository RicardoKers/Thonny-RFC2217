using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using System.Reflection;

[assembly: AssemblyTitle("Thonny RFC2217")]
[assembly: AssemblyProduct("Thonny RFC2217 (unofficial)")]
[assembly: AssemblyCompany("RicardoKers")]
[assembly: AssemblyVersion("0.1.1.0")]
[assembly: AssemblyFileVersion("0.1.1.0")]

internal static class Launcher
{
    private static string Quote(string value)
    {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { result.Append('\\', 2 * slashes + 1); result.Append(c); }
            else { result.Append('\\', slashes); result.Append(c); }
            slashes = 0;
        }
        result.Append('\\', 2 * slashes);
        return result.Append('"').ToString();
    }

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string python = Path.Combine(root, "pythonw.exe");
            string bootstrap = Path.Combine(root, "launch_thonny.py");
            if (!File.Exists(python) || !File.Exists(bootstrap))
                throw new FileNotFoundException("The application runtime is incomplete. Extract the full portable ZIP or reinstall Thonny RFC2217.");
            var start = new ProcessStartInfo(python);
            start.Arguments = "-I " + Quote(bootstrap) + " " + String.Join(" ", args.Select(Quote));
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            using (var process = Process.Start(start))
            {
                process.WaitForExit();
                return process.ExitCode;
            }
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Thonny RFC2217", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
