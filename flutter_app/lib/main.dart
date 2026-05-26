import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Video+ZIP OCR Search',
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.teal),
      home: const UploadPage(),
    );
  }
}

class UploadPage extends StatefulWidget {
  const UploadPage({super.key});

  @override
  State<UploadPage> createState() => _UploadPageState();
}

class _UploadPageState extends State<UploadPage> {
  PlatformFile? videoFile;
  PlatformFile? zipFile;
  String? zipId;
  String output = '';
  bool loading = false;

  Future<void> pickFile(bool isVideo) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: isVideo ? ['mp4', 'mov', 'mkv'] : ['zip'],
      withData: false,
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        if (isVideo) {
          videoFile = result.files.first;
        } else {
          zipFile = result.files.first;
        }
      });
      if (!isVideo) {
        await preloadZip();
      }
    }
  }



  Future<void> preloadZip() async {
    if (zipFile?.path == null) return;
    final dio = Dio();
    setState(() => output = 'ZIP解压中...');
    final resp = await dio.post(
      'http://127.0.0.1:8001/zip/preload',
      data: FormData.fromMap({
        'zip_file': await MultipartFile.fromFile(zipFile!.path!),
      }),
    );
    setState(() {
      zipId = resp.data['zip_id'];
      output = 'ZIP已解压, zip_id=$zipId, file_count=${resp.data['file_count']}';
    });
  }

  Future<void> runPipeline() async {
    if (videoFile?.path == null || zipFile?.path == null || zipId == null) {
      setState(() => output = '请先选择视频并先上传ZIP完成解压');
      return;
    }

    setState(() {
      loading = true;
      output = '处理中...';
    });

    final dio = Dio();
    try {
      final ocrResp = await dio.post(
        'http://127.0.0.1:8001/ocr/timestamps',
        data: FormData.fromMap({
          'video': await MultipartFile.fromFile(videoFile!.path!),
        }),
      );

      final timestamps = (ocrResp.data['timestamps'] as List).cast<String>();

      final searchResp = await dio.post(
        'http://127.0.0.1:8001/search/in-zip-by-id',
        data: FormData.fromMap({
          'zip_id': zipId,
          'timestamps_json': jsonEncode(timestamps),
        }),
      );

      setState(() {
        output = '完成:\n${searchResp.data}';
      });
    } catch (e) {
      setState(() => output = '出错: $e');
    } finally {
      setState(() => loading = false);
    }
  }

  Widget card({required String title, required PlatformFile? file, required VoidCallback onTap}) {
    return Card(
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          width: 320,
          height: 140,
          child: Center(
            child: Text(file == null ? '点击选择$title' : '已选择: ${file.name}'),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('拖拽视频+ZIP 检索')), 
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Wrap(
              spacing: 16,
              children: [
                card(title: '视频', file: videoFile, onTap: () => pickFile(true)),
                card(title: 'ZIP', file: zipFile, onTap: () => pickFile(false)),
              ],
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: loading ? null : runPipeline,
              child: Text(loading ? '处理中...' : '开始处理'),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: 900,
              child: SelectableText(output),
            )
          ],
        ),
      ),
    );
  }
}
