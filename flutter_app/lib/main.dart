import 'package:flutter/material.dart';

void main() => runApp(const ZirroApp());

const _bg = Color(0xFF080B12);
const _panel = Color(0xFF121824);
const _line = Color(0xFF273144);
const _accent = Color(0xFF8B7CFF);

class ZirroApp extends StatelessWidget {
  const ZirroApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ZIRRO AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: _bg,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _accent,
          brightness: Brightness.dark,
          surface: _panel,
        ),
        useMaterial3: true,
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _panel,
          hintStyle: const TextStyle(color: Color(0xFF8993A6)),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(24),
            borderSide: const BorderSide(color: _line),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(24),
            borderSide: const BorderSide(color: _line),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(24),
            borderSide: const BorderSide(color: _accent),
          ),
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
  void dispose() {
    _composer.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _send() {
    final text = _composer.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _messages.add(ChatMessage(text, fromUser: true));
      _messages.add(const ChatMessage(
        'The Flutter interface is ready, but AI account authentication and '
        'responses are not connected yet. This prototype does not send your '
        'message to any AI provider.',
        fromUser: false,
      ));
      _composer.clear();
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: _bg,
        titleSpacing: 18,
        title: Row(
          children: [
            Container(
              height: 36,
              width: 36,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                gradient: const LinearGradient(
                  colors: [_accent, Color(0xFF52D9D0)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: const Icon(Icons.auto_awesome_rounded,
                  color: Colors.white, size: 21),
            ),
            const SizedBox(width: 10),
            const Text('ZIRRO AI',
                style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: .4)),
          ],
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: _messages.isEmpty ? _welcome() : _messageList(),
            ),
            _composerBar(),
          ],
        ),
      ),
    );
  }

  Widget _welcome() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(26, 18, 26, 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              height: 76,
              width: 76,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(26),
                gradient: const LinearGradient(
                  colors: [_accent, Color(0xFF52D9D0)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                boxShadow: [
                  BoxShadow(
                    color: _accent.withValues(alpha: .2),
                    blurRadius: 32,
                    spreadRadius: 1,
                  ),
                ],
              ),
              child: const Icon(Icons.auto_awesome_rounded,
                  color: Colors.white, size: 36),
            ),
            const SizedBox(height: 24),
            const Text(
              'Your ideas, amplified.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 10),
            const Text(
              'A fresh space to think, create, and explore.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF9CA8BB), fontSize: 15),
            ),
            const SizedBox(height: 28),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 9,
              runSpacing: 9,
              children: const [
                _Suggestion(icon: Icons.edit_note_rounded, text: 'Write something'),
                _Suggestion(icon: Icons.code_rounded, text: 'Build an app'),
                _Suggestion(icon: Icons.lightbulb_outline, text: 'Explore an idea'),
              ],
            ),
            const SizedBox(height: 20),
            const Text(
              'Prototype mode · AI is not connected yet',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF69758A), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _messageList() {
    return ListView.builder(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
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
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
            decoration: BoxDecoration(
              color: message.fromUser ? const Color(0xFF292449) : _panel,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: message.fromUser
                    ? _accent.withValues(alpha: .35)
                    : _line,
              ),
            ),
            child: Text(message.text, style: const TextStyle(height: 1.45)),
          ),
        );
      },
    );
  }

  Widget _composerBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
      decoration: const BoxDecoration(
        color: _bg,
        border: Border(top: BorderSide(color: Color(0xFF1B2331))),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: TextField(
              controller: _composer,
              minLines: 1,
              maxLines: 5,
              textInputAction: TextInputAction.newline,
              onSubmitted: (_) => _send(),
              decoration: const InputDecoration(
                hintText: 'Message ZIRRO...',
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 18, vertical: 13),
              ),
            ),
          ),
          const SizedBox(width: 9),
          SizedBox(
            height: 49,
            width: 49,
            child: FilledButton(
              onPressed: _send,
              style: FilledButton.styleFrom(
                padding: EdgeInsets.zero,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(17),
                ),
              ),
              child: const Icon(Icons.arrow_upward_rounded),
            ),
          ),
        ],
      ),
    );
  }
}

class _Suggestion extends StatelessWidget {
  const _Suggestion({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _line),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 17, color: _accent),
          const SizedBox(width: 7),
          Text(text, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}
