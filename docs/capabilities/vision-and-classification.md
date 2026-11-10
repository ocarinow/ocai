# Standalone vision and classification endpoints — deferred summary

**Currency:** researched 2026-11-10 against official documentation. Short on
purpose: this family is deferred. Items marked *unverified* rest on
third-party sources or pages not re-read on the read date.

## 1. What exists

| Service | Endpoint / op | Input | Output shape | Status (read date) | Billing |
|---|---|---|---|---|---|
| Google Cloud Vision | `POST https://vision.googleapis.com/v1/images:annotate` with `requests[] {image {content | source {imageUri, gcsImageUri}}, features[] {type, maxResults, model}, imageContext}`; `parent` for `us`/`eu` | base64 or GCS/URL | `responses[] {labelAnnotations[] {mid, description, score, topicality}, localizedObjectAnnotations[] {name, score, boundingPoly {normalizedVertices}}, textAnnotations, fullTextAnnotation, safeSearchAnnotation {adult, spoof, medical, violence, racy}, faceAnnotations, logoAnnotations, webDetection, cropHintsAnnotation, error}` (per-feature field names from the reference; the method page itself only names `AnnotateImageRequest`/`BatchAnnotateImagesResponse`) | GA | first 1,000 units/month free; $1.50 / 1,000 units for most features, $1.00 above 5M (localized official page; *unverified* in English) |
| Azure AI Vision Image Analysis 4.0 | `POST {endpoint}/computervision/imageanalysis:analyze?api-version=2024-02-01&features=caption,denseCaptions,tags,objects,people,read,smartCrops` (path from memory; *unverified*) | binary or `{url}`; ≤ 20 MB, 50×50–16,000×16,000 px | `captionResult`, `denseCaptionsResult`, `tagsResult`, `objectsResult` (boxes), `peopleResult`, `readResult` (lines/words/polygons), `smartCropsResult` | **Deprecated: retires 2028-09-25.** Custom classification/detection, product recognition and segmentation previews retired 2025-03-31 (use Custom Vision) | per 1,000 transactions (not on page) |
| AWS Rekognition | `DetectLabels {Image {Bytes | S3Object}, MaxLabels, MinConfidence (default 55), Features [GENERAL_LABELS, IMAGE_PROPERTIES], Settings {GeneralLabels {Label*Filters}, ImageProperties {MaxDominantColors}}}`; siblings `DetectText`, `DetectFaces`, `DetectModerationLabels`, `RecognizeCelebrities`, `DetectCustomLabels` | JPEG/PNG bytes or S3 | `Labels[] {Name, Confidence, Instances[] {BoundingBox {Left, Top, Width, Height}, Confidence, DominantColors}, Parents[], Aliases[], Categories[]}, ImageProperties {Quality, DominantColors, Foreground, Background}, LabelModelVersion` | GA | ≈ $0.001 / image first 1M (pricing examples; *unverified* full tier table) |
| Clarifai | `POST /v2/users/{user_id}/apps/{app_id}/models/{model_id}/versions/{version_id}/outputs` (official docs still show `/v2/models/{id}/versions/{v}/outputs`), `Authorization: Key <PAT>` | `inputs[] {data {image {url | base64}}}` | `outputs[] {data {concepts[] {id, name, value}, regions[] {region_info {bounding_box}, data {concepts}}}}` (`regions` shape *unverified*); `max_concepts` in `output_config` (default 20) | active; docs host unreachable on the read date (DNS) | per operation (*unverified*) |
| Roboflow hosted inference | `POST https://serverless.roboflow.com/{projectId}/{versionNumber}` (also `detect.roboflow.com` legacy), `Authorization: Bearer` or `api_key` param; `image` URL param or base64 body; `confidence`, `overlap`, `classes`, `format: json|image` | custom-trained detectors/classifiers; workflows | `predictions[] {x, y, width, height, class, confidence}, image {width, height}` (centre-point boxes in pixels) | GA; self-hostable `roboflow/inference` | per credit / plan (*unverified*) |
| Hugging Face Inference Providers | `POST https://router.huggingface.co/{provider}/models/{model}` per task, `Authorization: Bearer hf_…` | binary image or `{inputs: base64, parameters {function_to_apply, top_k}}` | image-classification `[{label, score}]`; object-detection `[{label, score, box {xmin, ymin, xmax, ymax}}]`; image-segmentation `[{label, score, mask}]`; zero-shot with `candidate_labels` | GA; any public checkpoint | provider compute rates; PRO monthly credits |
| Cohere `classify` | `POST /v1/classify` | texts + examples | `classifications[] {prediction, confidence, labels}` | **Deprecated.** Classify on default embed models ended 2025-01-31; fine-tuned Classify is still documented but the 2025-09 fine-tuning retirement makes its future unclear (*unverified*) | per classification |
| OpenAI moderation | `POST /v1/moderations`, `omni-moderation-latest`, `input` string or `[{type: text} | {type: image_url}]` | text + images ≤ 20 MB | `results[] {flagged, categories {13 keys}, category_scores, category_applied_input_types}` | GA, free | free |

Text classifiers and moderation endpoints (OpenAI moderation, Azure Content
Safety, Perspective, Mistral moderation) are the H7 moderation capability and
are out of scope here except as a boundary note: moderation is a *different*
operation (policy categories with scores) from open-vocabulary classification.

## 2. Why most of this is covered by multimodal chat today

- Labels, captions, dense captions, visual question answering, OCR-lite and
  zero-shot classification are a `ChatRequest` with a `PartImage` and an
  `OutputFormat(mode="json_schema")` — one honest edge per chat interface
  already in scope, with the fidelity report attached. Azure is retiring
  exactly this slice of its vision product in favour of multimodal models.
- Open-vocabulary results beat fixed taxonomies for product use, and a
  JSON-schema output already gives the structured contract users wanted from
  `labelAnnotations` or `tagsResult`.
- Moderation is a separate, already-planned capability (H7), so the
  "classification" people most often need from these endpoints is covered by
  a sibling.

## 3. What multimodal chat does **not** cover (the revisit triggers)

1. **Dense geometry at volume** — detection boxes, segmentation masks, face
   landmarks: chat models return approximate coordinates, no masks, and cost
   tokens per image rather than ≈ $1 / 1,000 images.
2. **Custom-trained models** — Roboflow, Rekognition Custom Labels, Custom
   Vision, HF checkpoints: a deployed model with a fixed label space and a
   confidence threshold is a different contract from generation.
3. **Determinism and audit** — classifier scores are reproducible and
   thresholdable; generated labels are not. Enterprises with existing model
   governance will want the classifier shape.
4. **Identity-adjacent features** (faces, celebrities) carry policy
   constraints ocai should not launder through a generic edge.

If two product requests arrive that need boxes or masks across ≥2 vendors,
the capability would be `vision` with operations `classify` (open label
list with scores) and `detect` (instances with `BBox` + label + score,
reusing the `BBox(x0, y0, x1, y1, unit, origin)` type proposed for
`document.parse`), `Source` for input, `Consumption(images=…)` for usage.
Declared loss would be centre-point vs corner boxes (Roboflow vs Rekognition
vs Google normalized vertices) and taxonomy hierarchy (`Parents[]` only on
Rekognition). The litmus test would pass; the demand does not yet.

## 4. Verdict

- **Deferred, P3.** Kernel-eligible by the litmus test (wire dialects do
  vary) but not product-relevant while multimodal chat plus the H7 moderation
  capability cover the demand, and while two of the eight incumbents are
  deprecating.
- Do not add vision-specific part types to the chat IR for this; `PartImage`
  plus `OutputFormat` is the honest path.
- Re-open when: a product needs detection boxes or masks from a provider
  endpoint; or a customer brings a custom-trained model behind Roboflow/
  Rekognition/HF that must be ledgered alongside chat calls.

## 5. Unverified / open

- Google Vision English pricing page and per-feature field names on the
  method page; Azure analyze path/version; Rekognition full tier table;
  Clarifai current path and `regions` fields (docs host unreachable);
  Roboflow and Clarifai pricing; Cohere fine-tuned Classify end date.

## Sources (read 2026-11-10)

- https://docs.cloud.google.com/vision/docs/reference/rest/v1/images/annotate
- https://cloud.google.com/vision/pricing
- https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/overview-image-analysis
- https://docs.aws.amazon.com/rekognition/latest/APIReference/API_DetectLabels.html
- https://aws.amazon.com/rekognition/pricing/
- https://docs.clarifai.com/api-guide/predict/images
- https://docs.roboflow.com/deploy/hosted-api/custom-models/object-detection
- https://huggingface.co/docs/inference-providers/tasks/image-classification
- https://docs.cohere.com/v2/docs/deprecations
- https://docs.cohere.com/changelog/classify-default-model-deprecation
- https://developers.openai.com/api/docs/guides/moderation
