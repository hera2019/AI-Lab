import Foundation
import CoreImage
import Vision

@main
struct AppleVisionReceiptOCR {
    struct CandidateRecord: Codable {
        let text: String
        let confidence: Float
    }

    struct ObservationRecord: Codable {
        let x: Double
        let y: Double
        let width: Double
        let height: Double
        let candidates: [CandidateRecord]
    }

    struct OCRExport: Codable {
        let sourceImage: String
        let elapsedSeconds: Double
        let observations: [ObservationRecord]
    }

    static func main() async {
        guard CommandLine.arguments.count == 4 else {
            FileHandle.standardError.write(Data("usage: apple_vision_receipt_ocr IMAGE RECTIFIED_IMAGE OCR_JSON\n".utf8))
            exit(2)
        }

        guard #available(macOS 26.0, *) else {
            FileHandle.standardError.write(Data("document recognition requires macOS 26 or later\n".utf8))
            exit(2)
        }

        let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
        let rectifiedURL = URL(fileURLWithPath: CommandLine.arguments[2])
        let jsonURL = URL(fileURLWithPath: CommandLine.arguments[3])

        do {
            let originalOCR = try await runTextRecognition(imageURL, label: "ORIGINAL")
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            try encoder.encode(originalOCR).write(to: jsonURL, options: .atomic)
            try await runDocumentRecognition(imageURL, label: "ORIGINAL")
            try await rectifyDocument(imageURL, outputURL: rectifiedURL)
            _ = try await runTextRecognition(rectifiedURL, label: "RECTIFIED")
            try await runDocumentRecognition(rectifiedURL, label: "RECTIFIED")
        } catch {
            FileHandle.standardError.write(Data("Vision error: \(error)\n".utf8))
            exit(1)
        }
    }

    @available(macOS 26.0, *)
    static func rectifyDocument(_ imageURL: URL, outputURL: URL) async throws {
        guard let image = CIImage(contentsOf: imageURL, options: [.applyOrientationProperty: true]) else {
            throw NSError(domain: "AppleVisionReceiptOCR", code: 1, userInfo: [NSLocalizedDescriptionKey: "unable to load image"])
        }

        let start = CFAbsoluteTimeGetCurrent()
        let observation = try await DetectDocumentSegmentationRequest().perform(on: image)
        let elapsed = CFAbsoluteTimeGetCurrent() - start

        guard let observation else {
            throw NSError(domain: "AppleVisionReceiptOCR", code: 2, userInfo: [NSLocalizedDescriptionKey: "no document detected"])
        }

        func imagePoint(_ point: NormalizedPoint) -> CGPoint {
            CGPoint(
                x: image.extent.minX + point.x * image.extent.width,
                y: image.extent.minY + point.y * image.extent.height
            )
        }

        let topLeft = imagePoint(observation.topLeft)
        let topRight = imagePoint(observation.topRight)
        let bottomRight = imagePoint(observation.bottomRight)
        let bottomLeft = imagePoint(observation.bottomLeft)

        let rectified = image.applyingFilter(
            "CIPerspectiveCorrection",
            parameters: [
                "inputTopLeft": CIVector(cgPoint: topLeft),
                "inputTopRight": CIVector(cgPoint: topRight),
                "inputBottomRight": CIVector(cgPoint: bottomRight),
                "inputBottomLeft": CIVector(cgPoint: bottomLeft),
            ]
        )

        guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB) else {
            throw NSError(domain: "AppleVisionReceiptOCR", code: 3, userInfo: [NSLocalizedDescriptionKey: "unable to create color space"])
        }

        try CIContext().writePNGRepresentation(
            of: rectified,
            to: outputURL,
            format: .RGBA8,
            colorSpace: colorSpace
        )

        print("===== APPLE-VISION-DOCUMENT-SEGMENTATION =====")
        print(String(format: "elapsed_seconds=%.4f", elapsed))
        print(String(format: "top_left=%.4f,%.4f", observation.topLeft.x, observation.topLeft.y))
        print(String(format: "top_right=%.4f,%.4f", observation.topRight.x, observation.topRight.y))
        print(String(format: "bottom_right=%.4f,%.4f", observation.bottomRight.x, observation.bottomRight.y))
        print(String(format: "bottom_left=%.4f,%.4f", observation.bottomLeft.x, observation.bottomLeft.y))
        print("rectified_image=\(outputURL.path)")
    }

    @available(macOS 26.0, *)
    static func runTextRecognition(_ imageURL: URL, label: String) async throws -> OCRExport {
        var request = RecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = [
            Locale.Language(identifier: "ja-JP"),
            Locale.Language(identifier: "en-US"),
        ]
        request.automaticallyDetectsLanguage = true
        request.usesLanguageCorrection = true
        request.minimumTextHeightFraction = 0.003

        let start = CFAbsoluteTimeGetCurrent()
        let observations = try await request.perform(on: imageURL)
        let elapsed = CFAbsoluteTimeGetCurrent() - start

        let sorted = observations.sorted { lhs, rhs in
            if abs(lhs.topLeft.y - rhs.topLeft.y) > 0.01 {
                return lhs.topLeft.y > rhs.topLeft.y
            }
            return lhs.topLeft.x < rhs.topLeft.x
        }

        print("===== APPLE-VISION-TEXT-\(label) =====")
        print(String(format: "elapsed_seconds=%.4f", elapsed))
        print("observations=\(sorted.count)")

        var records: [ObservationRecord] = []
        for observation in sorted {
            let candidates = observation.topCandidates(3)
            guard let candidate = candidates.first else {
                continue
            }
            let x = min(observation.topLeft.x, observation.bottomLeft.x)
            let y = min(observation.bottomLeft.y, observation.bottomRight.y)
            let width = max(observation.topRight.x, observation.bottomRight.x) - x
            let height = max(observation.topLeft.y, observation.topRight.y) - y
            records.append(ObservationRecord(
                x: Double(x),
                y: Double(y),
                width: Double(width),
                height: Double(height),
                candidates: candidates.map {
                    CandidateRecord(text: $0.string, confidence: $0.confidence)
                }
            ))
            print(String(
                format: "x=%.4f y=%.4f w=%.4f h=%.4f confidence=%.4f | %@",
                x,
                y,
                width,
                height,
                candidate.confidence,
                candidate.string
            ))
            let alternatives = candidates.dropFirst().map {
                String(format: "%.4f:%@", $0.confidence, $0.string)
            }
            if !alternatives.isEmpty {
                print("  alternatives=\(alternatives.joined(separator: " || "))")
            }
        }

        return OCRExport(
            sourceImage: imageURL.path,
            elapsedSeconds: elapsed,
            observations: records
        )
    }

    @available(macOS 26.0, *)
    static func runDocumentRecognition(_ imageURL: URL, label: String) async throws {
        var request = RecognizeDocumentsRequest()
        var options = request.textRecognitionOptions
        options.recognitionLanguages = [
            Locale.Language(identifier: "ja-JP"),
            Locale.Language(identifier: "en-US"),
        ]
        options.automaticallyDetectLanguage = true
        options.useLanguageCorrection = true
        options.minimumTextHeightFraction = 0.003
        options.maximumCandidateCount = 3
        request.textRecognitionOptions = options

        let start = CFAbsoluteTimeGetCurrent()
        let documents = try await request.perform(on: imageURL)
        let elapsed = CFAbsoluteTimeGetCurrent() - start

        print("===== APPLE-VISION-DOCUMENT-\(label) =====")
        print(String(format: "elapsed_seconds=%.4f", elapsed))
        print("documents=\(documents.count)")

        for (documentIndex, observation) in documents.enumerated() {
            let document = observation.document
            print("----- document=\(documentIndex) transcript -----")
            print(document.text.transcript)
            print("----- document=\(documentIndex) tables=\(document.tables.count) -----")

            for (tableIndex, table) in document.tables.enumerated() {
                print("table=\(tableIndex) rows=\(table.rows.count) columns=\(table.columns.count)")
                for row in table.rows {
                    for cell in row {
                        let text = cell.content.text.transcript.replacingOccurrences(of: "\n", with: " ")
                        print(
                            "row=\(cell.rowRange.lowerBound)-\(cell.rowRange.upperBound) "
                                + "column=\(cell.columnRange.lowerBound)-\(cell.columnRange.upperBound) "
                                + "text=\(text)"
                        )
                    }
                }
            }
        }
    }
}
