import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

void main() => runApp(const ZirroApp());

const _background = Color(0xFF070A12);
const _accent = Color(0xFF9B8CFF);
const _siteUrl = 'https://zirro.onrender.com';

class ZirroApp extends StatelessWidget {
  const ZirroApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ZIRRO AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: _background,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _accent,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const ZirroWebsiteScreen(),
    );
  }
}

class ZirroWebsiteScreen extends StatefulWidget {
  const ZirroWebsiteScreen({super.key});

  @override
  State<ZirroWebsiteScreen> createState() => _ZirroWebsiteScreenState();
}

class _ZirroWebsiteScreenState extends State<ZirroWebsiteScreen> {
  late final WebViewController _web;
  int _progress = 0;
  bool _loading = true;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(_background)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (progress) {
            if (mounted) {
              setState(() {
                _progress = progress;
                _loading = progress < 100;
                if (progress > 10) _loadError = null;
              });
            }
          },
          onPageStarted: (_) {
            if (mounted) {
              setState(() {
                _loading = true;
                _progress = 0;
                _loadError = null;
              });
            }
          },
          onPageFinished: (_) {
            if (mounted) {
              setState(() {
                _loading = false;
                _progress = 100;
              });
            }
          },
          onWebResourceError: (error) {
            if (error.isForMainFrame == true && mounted) {
              setState(() {
                _loading = false;
                _loadError = 'ZIRRO could not load. Check your internet connection and try again.';
              });
            }
          },
          onNavigationRequest: (request) async {
            final uri = Uri.tryParse(request.url);
            if (uri == null) return NavigationDecision.prevent;
            if (uri.scheme == 'http' || uri.scheme == 'https') {
              // Keep ZIRRO pages and their website features inside the app.
              if (uri.host == 'zirro.onrender.com' ||
                  uri.host.endsWith('.onrender.com')) {
                return NavigationDecision.navigate;
              }
              // External sites still open safely in the device browser.
              await launchUrl(uri, mode: LaunchMode.externalApplication);
              return NavigationDecision.prevent;
            }
            if (uri.scheme == 'mailto' || uri.scheme == 'tel') {
              await launchUrl(uri, mode: LaunchMode.externalApplication);
            }
            return NavigationDecision.prevent;
          },
        ),
      )
      ..loadRequest(Uri.parse(_siteUrl));
  }

  Future<void> _reload() async {
    setState(() {
      _loading = true;
      _loadError = null;
      _progress = 0;
    });
    await _web.loadRequest(Uri.parse(_siteUrl));
  }

  @override
  Widget build(BuildContext context) {
    return PopScope<Object?>(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        if (await _web.canGoBack()) {
          await _web.goBack();
        } else {
          await SystemNavigator.pop();
        }
      },
      child: Scaffold(
        body: SafeArea(
          child: Column(
            children: [
              if (_loading)
                LinearProgressIndicator(
                  value: _progress == 0 ? null : _progress / 100,
                  minHeight: 2,
                  backgroundColor: const Color(0xFF151A29),
                  color: _accent,
                ),
              Expanded(
                child: Stack(
                  children: [
                    WebViewWidget(controller: _web),
                    if (_loadError != null)
                      Positioned.fill(
                        child: ColoredBox(
                          color: _background,
                          child: Center(
                            child: Padding(
                              padding: const EdgeInsets.all(28),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.wifi_off_rounded,
                                      size: 54, color: _accent),
                                  const SizedBox(height: 18),
                                  const Text(
                                    'Unable to connect to ZIRRO',
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.w700,
                                    ),
                                    textAlign: TextAlign.center,
                                  ),
                                  const SizedBox(height: 10),
                                  Text(
                                    _loadError!,
                                    style: const TextStyle(
                                        color: Color(0xFF9CA9C2)),
                                    textAlign: TextAlign.center,
                                  ),
                                  const SizedBox(height: 22),
                                  FilledButton.icon(
                                    onPressed: _reload,
                                    icon: const Icon(Icons.refresh_rounded),
                                    label: const Text('Try again'),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
