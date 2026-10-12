import 'dart:convert';
import 'dart:ui';

import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

import 'package:flutter/material.dart';

void main() => runApp(const ZirroApp());

const _bg = Color(0xFF070A12);
const _glass = Color(0x18FFFFFF);
const _stroke = Color(0x30FFFFFF);
const _muted = Color(0xFF9CA9C2);
const _violet = Color(0xFF9B8CFF);
const _cyan = Color(0xFF71E5E0);

class ZirroApp extends StatelessWidget {
  const ZirroApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ZIRRO AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        scaffoldBackgroundColor: _bg,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _violet,
          brightness: Brightness.dark,
        ),
      ),
      home: const ChatHome(),
    );
  }
}

class ChatMessage {
  const ChatMessage(this.text, {required this.fromUser});
  final String text;
  final bool fromUser;
}

class ChatHome extends StatefulWidget {
  const ChatHome({super.key});

  @override
  State<ChatHome> createState() => _ChatHomeState();
}

class _ChatHomeState extends State<ChatHome> {
  final _composer = TextEditingController();
  final _scroll = ScrollController();
  final List<ChatMessage> _messages = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkForAppUpdate());
  }

  static const int _installedBuildNumber =
      int.fromEnvironment('ZIRRO_BUILD_NUMBER', defaultValue: 0);

  Future<void> _checkForAppUpdate() async {
    try {
      final response = await http.get(
        Uri.parse('https://api.github.com/repos/emzaro731-byte/zirro/releases/latest'),
        headers: const {'Accept': 'application/vnd.github+json'},
      ).timeout(const Duration(seconds: 8));
      if (response.statusCode != 200 || !mounted) return;

      final release = jsonDecode(response.body) as Map<String, dynamic>;
      final tag = (release['tag_name'] ?? '').toString();
      final match = RegExp(r'^build-(\d+)$').firstMatch(tag);
      if (match == null) return;
      final latestBuild = int.tryParse(match.group(1) ?? '') ?? 0;
      if (latestBuild <= _installedBuildNumber || !mounted) return;

      final releaseUrl = Uri.tryParse(
        (release['html_url'] ?? 'https://github.com/emzaro731-byte/zirro/releases/latest').toString(),
      );
      if (releaseUrl == null) return;

      final shouldOpen = await showDialog<bool>(
        context: context,
        barrierDismissible: true,
        builder: (dialogContext) => AlertDialog(
          title: const Text('ZIRRO update available'),
          content: Text(
            'Build $latestBuild is available. Open GitHub Releases to download and install the latest APK.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Later'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Get update'),
            ),
          ],
        ),
      );
      if (shouldOpen == true) {
        await launchUrl(releaseUrl, mode: LaunchMode.externalApplication);
      }
    } catch (_) {
      // Updates are optional; do not block app startup if offline or GitHub is unavailable.
    }
  }

  @override
  void dispose() {
    _composer.dispose();
    _scroll.dispose();
    super.dispose();
  }

  bool _sending = false;

  Future<void> _send() async {
    final text = _composer.text.trim();
    if (text.isEmpty || _sending) return;

    final history = _messages
        .map((m) => <String, String>{
              'role': m.fromUser ? 'user' : 'assistant',
              'content': m.text,
            })
        .toList();

    setState(() {
      _sending = true;
      _messages.add(ChatMessage(text, fromUser: true));
      _messages.add(const ChatMessage('ZIRRO is thinking…', fromUser: false));
      _composer.clear();
    });
    _scrollToBottom();

    try {
      final response = await http
          .post(
            Uri.parse('https://zirro.onrender.com/api/chat'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({
              'provider': 'openrouter',
              'mode': 'chat',
              'message': text,
              'history': history,
            }),
          )
          .timeout(const Duration(seconds: 110));

      final decoded = jsonDecode(response.body);
      final data = decoded is Map<String, dynamic>
          ? decoded
          : <String, dynamic>{};
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception((data['error'] ?? 'AI request failed (HTTP ${response.statusCode}).').toString());
      }
      final reply = (data['reply'] ?? '').toString().trim();
      if (reply.isEmpty) throw Exception('The AI service returned an empty response.');

      if (!mounted) return;
      setState(() {
        _messages.removeLast();
        _messages.add(ChatMessage(reply, fromUser: false));
      });
    } catch (error) {
      if (!mounted) return;
      final message = error.toString().replaceFirst('Exception: ', '');
      setState(() {
        _messages.removeLast();
        _messages.add(ChatMessage(
          'Could not get an AI response: $message\n\nCheck that OPENROUTER_API_KEY is configured in Render and that the ZIRRO service is awake.',
          fromUser: false,
        ));
      });
    } finally {
      if (mounted) setState(() => _sending = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  void _usePrompt(String prompt) {
    _composer.text = prompt;
    _composer.selection = TextSelection.collapsed(offset: prompt.length);
    FocusScope.of(context).requestFocus(FocusNode());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: Stack(
        children: [
          const _LiquidBackdrop(),
          SafeArea(
            child: Column(
              children: [
                _topBar(),
                Expanded(
                  child: _messages.isEmpty ? _welcome() : _messageList(),
                ),
                _composerArea(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _topBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 14),
      child: Row(
        children: [
          Container(
            height: 43,
            width: 43,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [_violet, Color(0xFF7165D9), _cyan],
              ),
              boxShadow: [
                BoxShadow(
                  color: _violet.withValues(alpha: .28),
                  blurRadius: 24,
                  spreadRadius: -4,
                ),
              ],
            ),
            child: const Icon(Icons.auto_awesome_rounded,
                color: Colors.white, size: 23),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ZIRRO',
                  style: TextStyle(
                    fontSize: 18,
                    letterSpacing: 2.4,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'AI STUDIO',
                  style: TextStyle(
                    color: _muted,
                    fontSize: 9,
                    letterSpacing: 2.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          _GlassSurface(
            radius: 22,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.blur_on_rounded, size: 15, color: _cyan),
                SizedBox(width: 6),
                Text(
                  'GLASS UI',
                  style: TextStyle(
                    fontSize: 10,
                    letterSpacing: 1.1,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _welcome() {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(22, 18, 22, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              height: 116,
              width: 116,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    _cyan.withValues(alpha: .22),
                    _violet.withValues(alpha: .13),
                    Colors.transparent,
                  ],
                ),
              ),
              child: Center(
                child: Container(
                  height: 70,
                  width: 70,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(26),
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFFB5ACFF), _violet, Color(0xFF4BCAC8)],
                    ),
                    border: Border.all(color: Colors.white.withValues(alpha: .6)),
                    boxShadow: [
                      BoxShadow(
                        color: _violet.withValues(alpha: .32),
                        blurRadius: 35,
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.auto_awesome_rounded,
                      size: 34, color: Colors.white),
                ),
              ),
            ),
          ),
          const SizedBox(height: 15),
          const Center(
            child: Text(
              'A little more\npossibility.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 35,
                height: 1.08,
                letterSpacing: -1.3,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(height: 12),
          const Center(
            child: Text(
              'Your creative space, wrapped in glass.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, fontSize: 14, height: 1.5),
            ),
          ),
          const SizedBox(height: 25),
          const Row(
            children: [
              Text(
                'START WITH AN IDEA',
                style: TextStyle(
                  color: Color(0xFF8794AE),
                  fontSize: 10,
                  letterSpacing: 2,
                  fontWeight: FontWeight.w700,
                ),
              ),
              SizedBox(width: 8),
              Expanded(child: Divider(color: _stroke, height: 1)),
            ],
          ),
          const SizedBox(height: 13),
          _promptTile(
            icon: Icons.edit_note_rounded,
            title: 'Write something',
            subtitle: 'Stories, captions, and fresh ideas',
            prompt: 'Help me write something creative',
            tint: _violet,
          ),
          const SizedBox(height: 10),
          _promptTile(
            icon: Icons.code_rounded,
            title: 'Build an app',
            subtitle: 'Turn a concept into a clear plan',
            prompt: 'Help me plan a mobile app',
            tint: _cyan,
          ),
          const SizedBox(height: 10),
          _promptTile(
            icon: Icons.lightbulb_outline_rounded,
            title: 'Explore an idea',
            subtitle: 'Think it through, one step at a time',
            prompt: 'Help me develop a new idea',
            tint: const Color(0xFFFFC98A),
          ),
          const SizedBox(height: 17),
          Center(
            child: _GlassSurface(
              radius: 20,
              padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.shield_outlined, color: _cyan, size: 14),
                  SizedBox(width: 7),
                  Text(
                    'CONNECTED TO ZIRRO AI  ·  OPENROUTER',
                    style: TextStyle(
                      color: _muted,
                      fontSize: 9,
                      letterSpacing: .8,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _promptTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required String prompt,
    required Color tint,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: () => _usePrompt(prompt),
        child: _GlassSurface(
          radius: 22,
          padding: const EdgeInsets.all(15),
          child: Row(
            children: [
              Container(
                height: 45,
                width: 45,
                decoration: BoxDecoration(
                  color: tint.withValues(alpha: .12),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: tint.withValues(alpha: .22)),
                ),
                child: Icon(icon, color: tint, size: 23),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(
                            fontWeight: FontWeight.w700, fontSize: 14)),
                    const SizedBox(height: 4),
                    Text(subtitle,
                        style: const TextStyle(color: _muted, fontSize: 11)),
                  ],
                ),
              ),
              const Icon(Icons.arrow_outward_rounded,
                  color: Color(0xFF9DA9BF), size: 17),
            ],
          ),
        ),
      ),
    );
  }

  Widget _messageList() {
    return ListView.builder(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 22),
      itemCount: _messages.length,
      itemBuilder: (context, index) {
        final message = _messages[index];
        return Align(
          alignment:
              message.fromUser ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.sizeOf(context).width * .84,
            ),
            margin: const EdgeInsets.only(bottom: 12),
            child: _GlassSurface(
              radius: 22,
              fill: message.fromUser
                  ? const Color(0x2C9B8CFF)
                  : const Color(0x20FFFFFF),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
              child: Text(
                message.text,
                style: const TextStyle(height: 1.5, fontSize: 14),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _composerArea() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 13),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _GlassSurface(
            radius: 28,
            fill: const Color(0x2A171D2D),
            padding: const EdgeInsets.fromLTRB(7, 7, 7, 7),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                IconButton(
                  tooltip: 'Add attachment',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Attachments are not supported in this version yet.'),
                      ),
                    );
                  },
                  icon: const Icon(Icons.add_rounded, color: _muted),
                ),
                Expanded(
                  child: TextField(
                    controller: _composer,
                    minLines: 1,
                    maxLines: 5,
                    textInputAction: TextInputAction.newline,
                    onSubmitted: (_) => _send(),
                    decoration: const InputDecoration(
                      hintText: 'Ask ZIRRO anything...',
                      hintStyle: TextStyle(color: Color(0xFF8995AD)),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.fromLTRB(4, 14, 4, 13),
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                Container(
                  height: 46,
                  width: 46,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(19),
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [_violet, Color(0xFF7770E8), _cyan],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: _violet.withValues(alpha: .25),
                        blurRadius: 18,
                        spreadRadius: -3,
                      ),
                    ],
                  ),
                  child: IconButton(
                    onPressed: _sending ? null : _send,
                    tooltip: 'Send message',
                    icon: _sending
                        ? const SizedBox(width: 19, height: 19, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.arrow_upward_rounded, color: Colors.white, size: 21),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 9),
          const Text(
            'ZIRRO AI  ·  POWERED BY OPENROUTER',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Color(0xFF68758E),
              fontSize: 9,
              letterSpacing: 1.2,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _GlassSurface extends StatelessWidget {
  const _GlassSurface({
    required this.child,
    this.radius = 24,
    this.padding = EdgeInsets.zero,
    this.fill = _glass,
  });

  final Widget child;
  final double radius;
  final EdgeInsetsGeometry padding;
  final Color fill;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: fill,
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(color: _stroke, width: 1),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: .12),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}

class _LiquidBackdrop extends StatelessWidget {
  const _LiquidBackdrop();

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [_bg, Color(0xFF10152A), Color(0xFF080E17)],
          ),
        ),
        child: Stack(
          children: [
            Positioned(
              top: -110,
              right: -95,
              child: _GlowOrb(
                size: 290,
                color: _violet.withValues(alpha: .25),
              ),
            ),
            Positioned(
              top: 260,
              left: -150,
              child: _GlowOrb(
                size: 300,
                color: _cyan.withValues(alpha: .13),
              ),
            ),
            Positioned(
              bottom: -160,
              right: -80,
              child: _GlowOrb(
                size: 330,
                color: const Color(0xFF5865D9).withValues(alpha: .18),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});
  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ImageFiltered(
      imageFilter: ImageFilter.blur(sigmaX: 55, sigmaY: 55),
      child: Container(
        height: size,
        width: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [color, color.withValues(alpha: .02), Colors.transparent],
          ),
        ),
      ),
    );
  }
}
