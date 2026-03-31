const express = require("express");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const app = express();
const port = process.env.PORT || 3000;
const storageRoot = path.resolve(process.env.JOB_STORAGE_ROOT || "/data/jobs");
const workerScript = path.join(__dirname, "merge_worker.js");

app.use(express.json());

function assertPathWithinRoot(inputPath) {
	const resolvedPath = path.resolve(inputPath);
	const relativePath = path.relative(storageRoot, resolvedPath);

	if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
		throw new Error(`Path is outside JOB_STORAGE_ROOT: ${resolvedPath}`);
	}

	return resolvedPath;
}

app.get("/health", (_request, response) => {
	response.json({ status: "ok" });
});

app.post("/merge", async (request, response) => {
	try {
		const jobPath = assertPathWithinRoot(request.body.job_path);
		const mergeRequestPath = assertPathWithinRoot(request.body.merge_request_path);

		if (!fs.existsSync(jobPath)) {
			return response.status(404).json({ detail: `Job path not found: ${jobPath}` });
		}

		if (!fs.existsSync(mergeRequestPath)) {
			return response.status(404).json({
				detail: `Merge request not found: ${mergeRequestPath}`,
			});
		}

		await new Promise((resolve, reject) => {
			const child = spawn("node", [workerScript, mergeRequestPath], {
				cwd: __dirname,
				stdio: ["ignore", "pipe", "pipe"],
			});

			let stdout = "";
			let stderr = "";

			child.stdout.on("data", (chunk) => {
				stdout += chunk.toString();
			});

			child.stderr.on("data", (chunk) => {
				stderr += chunk.toString();
			});

			child.on("error", reject);
			child.on("close", (code) => {
				if (code !== 0) {
					reject(
						new Error(`Node merge worker failed.\nSTDOUT:\n${stdout}\nSTDERR:\n${stderr}`),
					);
					return;
				}

				resolve();
			});
		});

		const mergeResultPath = path.join(jobPath, "merge_result.json");
		if (!fs.existsSync(mergeResultPath)) {
			return response.status(500).json({
				detail: `Expected merge result file was not generated: ${mergeResultPath}`,
			});
		}

		response.json(JSON.parse(fs.readFileSync(mergeResultPath, "utf-8")));
	} catch (error) {
		response.status(500).json({ detail: error.message });
	}
});

app.listen(port, "0.0.0.0", () => {
	console.log(`Merge worker API listening on port ${port}`);
});
