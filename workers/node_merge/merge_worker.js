const fs = require("fs");
const path = require("path");
const Automizer = require("pptx-automizer").default;

async function main() {
	const requestPathArg = process.argv[2];

	if (!requestPathArg) {
		throw new Error("Missing merge request path");
	}

	const requestPath = path.resolve(requestPathArg);

	const request = JSON.parse(fs.readFileSync(requestPath, "utf-8"));
	const jobDir = path.dirname(requestPath);
	const outputPath = path.resolve(request.output);

	if (!Array.isArray(request.selection) || request.selection.length === 0) {
		throw new Error("Merge request must contain at least one selected slide");
	}

	const orderedSelection = [...request.selection].sort(
		(a, b) => a.output_position - b.output_position,
	);
	const uniqueSources = [
		...new Set(orderedSelection.map((item) => path.resolve(item.presentation_path))),
	];

	if (uniqueSources.length === 0) {
		throw new Error("No source presentations found in merge request");
	}

	for (const sourcePath of uniqueSources) {
		if (!fs.existsSync(sourcePath)) {
			throw new Error(`Missing source PPTX: ${sourcePath}`);
		}
	}

	fs.mkdirSync(path.dirname(outputPath), { recursive: true });

	const automizer = new Automizer({
		templateDir: "/",
		outputDir: path.dirname(outputPath),
		removeExistingSlides: true,
		autoImportSlideMasters: true,
	});

	// Use a deterministic root and truncate it via removeExistingSlides.
	automizer.loadRoot(uniqueSources[0]);

	const sourceAliasMap = new Map();
	for (const [index, sourcePath] of uniqueSources.entries()) {
		const alias = `src_${index}`;
		automizer.load(sourcePath, alias);
		sourceAliasMap.set(sourcePath, alias);
	}

	for (const item of orderedSelection) {
		const sourcePath = path.resolve(item.presentation_path);
		const sourceAlias = sourceAliasMap.get(sourcePath);

		if (!sourceAlias) {
			throw new Error(`Source alias not found for: ${sourcePath}`);
		}

		automizer.addSlide(sourceAlias, item.slide_index, (slide) => {
			slide.useSlideLayout();
		});
	}

	await automizer.write(path.basename(outputPath));

	const mergeResultPath = path.join(jobDir, "merge_result.json");
	const resultPayload = {
		status: "success",
		job_id: request.job_id,
		output: outputPath,
		slides_total: orderedSelection.length,
	};

	fs.writeFileSync(
		mergeResultPath,
		JSON.stringify(resultPayload, null, 2),
		"utf-8",
	);

	process.stdout.write(JSON.stringify(resultPayload));
}

main().catch((error) => {
	console.error(error);
	process.exit(1);
});
