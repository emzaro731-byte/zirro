import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

void main() => runApp(const ZirroApp());

const bg = Color(0xFF070A12);
const panel = Color(0xFF101522);
const accent = Color(0xFF9B8CFF);
const muted = Color(0xFF9CA9C2);
const api = 'https://zirro.onrender.com';

class ZirroApp extends StatelessWidget {
  const ZirroApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'ZIRRO AI', debugShowCheckedModeBanner: false,
    theme: ThemeData(brightness: Brightness.dark, scaffoldBackgroundColor: bg,
      colorScheme: ColorScheme.fromSeed(seedColor: accent, brightness: Brightness.dark),
      useMaterial3: true, inputDecorationTheme: InputDecorationTheme(
        filled: true, fillColor: const Color(0xFF171E2E),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none))),
    home: const ZirroHome(),
  );
}

class Msg {
  Msg(this.role, this.text);
  final String role;
  final String text;
}

class ZirroHome extends StatefulWidget {
  const ZirroHome({super.key});
  @override
  State<ZirroHome> createState() => _ZirroHomeState();
}

class _ZirroHomeState extends State<ZirroHome> {
  int tab = 0;
  bool sending = false, creating = false, checking = false, webSearch = false;
  String mode = 'chat', creation = 'image', status = '';
  String? error, resultUrl;
  final chatController = TextEditingController();
  final promptController = TextEditingController();
  final scrollController = ScrollController();
  final messages = <Msg>[];

  @override
  void dispose() {
    chatController.dispose();
    promptController.dispose();
    scrollController.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>> request(String path, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse(api + path);
    final response = body == null
      ? await http.get(uri).timeout(const Duration(seconds: 45))
      : await http.post(uri, headers: const {'Content-Type': 'application/json'},
          body: jsonEncode(body)).timeout(const Duration(seconds: 120));
    final Map<String, dynamic> data;
    try { data = jsonDecode(response.body) as Map<String, dynamic>; }
    catch (_) { throw Exception('ZIRRO returned an invalid response.'); }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(data['error']?.toString() ?? data['message']?.toString() ?? 'Request failed (' + response.statusCode.toString() + ').');
    }
    return data;
  }

  Future<void> sendChat() async {
    final text = chatController.text.trim();
    if (text.isEmpty || sending) return;
    setState(() { messages.add(Msg('user', text)); chatController.clear(); sending = true; error = null; });
    scrollToEnd();
    try {
      final history = messages.length > 1
        ? messages.sublist(0, messages.length - 1).take(16).map((m) => {'role': m.role, 'content': m.text}).toList()
        : <Map<String, String>>[];
      final data = await request('/api/chat', body: {
        'message': text, 'mode': mode, 'web_search': webSearch, 'history': history,
      });
      if (!mounted) return;
      setState(() => messages.add(Msg('assistant', data['reply']?.toString() ?? 'No response received.')));
      scrollToEnd();
    } catch (e) {
      if (mounted) setState(() => error = cleanError(e));
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  String cleanError(Object e) => e.toString().replaceFirst('Exception: ', '');

  void scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (scrollController.hasClients) scrollController.animateTo(
        scrollController.position.maxScrollExtent + 180,
        duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    });
  }

  Future<void> generate() async {
    final prompt = promptController.text.trim();
    if (prompt.isEmpty || creating) return;
    setState(() { creating = true; checking = false; resultUrl = null; error = null; status = 'Sending request…'; });
    try {
      final endpoint = creation == 'image' ? '/api/generate-image'
        : creation == 'video' ? '/api/generate-video' : '/api/generate-music';
      final data = await request(endpoint, body: {'prompt': prompt});
      final id = (data['task_id'] ?? data['job_id'] ?? data['prediction_id'])?.toString();
      if (id == null || id.isEmpty) throw Exception('The server did not return a generation task ID.');
      final statusPath = creation == 'image' ? '/api/image/status/' + id
        : creation == 'video' ? '/api/video/status/' + id : '/api/music/status/' + id;
      final resultKey = creation == 'image' ? 'image_url' : creation == 'video' ? 'video_url' : 'audio_url';
      setState(() => status = 'Generation is running. Keep this screen open…');
      for (var i = 0; i < 80; i++) {
        await Future<void>.delayed(const Duration(seconds: 4));
        if (!mounted) return;
        final result = await request(statusPath);
        final state = (result['status'] ?? 'processing').toString().toLowerCase();
        final url = result[resultKey]?.toString();
        if (url != null && url.startsWith('http')) {
          setState(() { resultUrl = url; status = 'Your ' + creation + ' is ready.'; });
          return;
        }
        final urls = result['urls'];
        if ((state == 'success' || state == 'succeeded' || state == 'completed' || state == 'complete') && urls is List && urls.isNotEmpty) {
          setState(() { resultUrl = urls.first.toString(); status = 'Your ' + creation + ' is ready.'; });
          return;
        }
        if (state == 'fail' || state == 'failed' || state == 'error' || state == 'cancelled') {
          throw Exception(result['error']?.toString() ?? 'The provider could not finish generation.');
        }
        setState(() => status = 'Generating ' + creation + '… (' + (i + 1).toString() + '/80)');
      }
      throw Exception('Generation is taking longer than expected. Check back later.');
    } catch (e) {
      if (mounted) setState(() { error = cleanError(e); status = ''; });
    } finally {
      if (mounted) setState(() { creating = false; checking = false; });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(backgroundColor: bg, titleSpacing: 18, title: Row(children: [
      Container(width: 38, height: 38, decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [accent, Color(0xFF55D6BE)]),
        borderRadius: BorderRadius.circular(13)),
        child: const Icon(Icons.auto_awesome_rounded, color: bg)),
      const SizedBox(width: 11),
      const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('ZIRRO', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.6)),
        Text('AI WORKSPACE', style: TextStyle(fontSize: 10, color: muted, letterSpacing: 1.8)),
      ]),
    ]), actions: [IconButton(onPressed: checkHealth, icon: const Icon(Icons.cloud_done_outlined)), const SizedBox(width: 5)]),
    body: IndexedStack(index: tab, children: [chatPage(), createPage(), settingsPage()]),
    bottomNavigationBar: NavigationBar(
      selectedIndex: tab, onDestinationSelected: (v) => setState(() => tab = v),
      backgroundColor: panel, indicatorColor: accent.withValues(alpha: 0.18),
      destinations: const [
        NavigationDestination(icon: Icon(Icons.chat_bubble_outline), selectedIcon: Icon(Icons.chat_bubble), label: 'Assistant'),
        NavigationDestination(icon: Icon(Icons.auto_awesome_outlined), selectedIcon: Icon(Icons.auto_awesome), label: 'Create'),
        NavigationDestination(icon: Icon(Icons.tune_rounded), selectedIcon: Icon(Icons.tune), label: 'Settings'),
      ]),
  );

  Widget chatPage() => Column(children: [
    Container(margin: const EdgeInsets.fromLTRB(16, 8, 16, 10), padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(gradient: const LinearGradient(colors: [Color(0xFF191B34), panel]),
        borderRadius: BorderRadius.circular(20), border: Border.all(color: accent.withValues(alpha: 0.22))),
      child: Row(children: [
        const Icon(Icons.bolt_rounded, color: accent), const SizedBox(width: 10),
        const Expanded(child: Text('What would you like to make happen?', style: TextStyle(fontWeight: FontWeight.w600))),
        PopupMenuButton<String>(initialValue: mode, onSelected: (v) => setState(() => mode = v),
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'chat', child: Text('Assistant')),
            PopupMenuItem(value: 'write', child: Text('Writer')),
            PopupMenuItem(value: 'code', child: Text('Code Studio')),
            PopupMenuItem(value: 'research', child: Text('Research')),
            PopupMenuItem(value: 'security', child: Text('Security Lab')),
            PopupMenuItem(value: 'documents', child: Text('Documents')),
          ], child: const Icon(Icons.expand_more_rounded, color: muted)),
      ])),
    Expanded(child: messages.isEmpty ? welcome() : ListView.builder(
      controller: scrollController, padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
      itemCount: messages.length + (sending ? 1 : 0),
      itemBuilder: (_, i) => i == messages.length
        ? const Bubble(isUser: false, text: 'Thinking…')
        : Bubble(isUser: messages[i].role == 'user', text: messages[i].text))),
    if (error != null && tab == 0) errorBanner(error!, () => setState(() => error = null)),
    Container(padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
      decoration: const BoxDecoration(color: bg, border: Border(top: BorderSide(color: Color(0xFF20283A)))),
      child: Column(children: [
        Row(children: [
          const Icon(Icons.travel_explore, size: 17, color: muted), const SizedBox(width: 6),
          const Text('Live web search', style: TextStyle(color: muted, fontSize: 12)), const Spacer(),
          Switch.adaptive(value: webSearch, onChanged: (v) => setState(() => webSearch = v)),
        ]),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Expanded(child: TextField(controller: chatController, minLines: 1, maxLines: 5,
            textInputAction: TextInputAction.send, onSubmitted: (_) => sendChat(),
            decoration: const InputDecoration(hintText: 'Message ZIRRO…', prefixIcon: Icon(Icons.add_rounded, color: muted),
              contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 14)))),
          const SizedBox(width: 8),
          SizedBox(height: 52, width: 52, child: FilledButton(
            onPressed: sending ? null : sendChat,
            style: FilledButton.styleFrom(padding: EdgeInsets.zero, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(17))),
            child: sending ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.arrow_upward_rounded))),
        ]),
      ])),
  ]);

  Widget welcome() => Center(child: SingleChildScrollView(padding: const EdgeInsets.all(22), child: Column(
    mainAxisAlignment: MainAxisAlignment.center, children: [
      Container(width: 82, height: 82, decoration: BoxDecoration(shape: BoxShape.circle,
        color: accent.withValues(alpha: 0.10), border: Border.all(color: accent.withValues(alpha: 0.3))),
        child: const Icon(Icons.auto_awesome_rounded, color: accent, size: 40)),
      const SizedBox(height: 22),
      const Text('Ideas become extraordinary.', textAlign: TextAlign.center,
        style: TextStyle(fontSize: 25, fontWeight: FontWeight.w800, letterSpacing: -0.6)),
      const SizedBox(height: 9),
      const Text('Chat, write, code, research, and create with ZIRRO AI.',
        textAlign: TextAlign.center, style: TextStyle(color: muted, height: 1.5)),
      const SizedBox(height: 26),
      Wrap(spacing: 9, runSpacing: 9, alignment: WrapAlignment.center, children: [
        suggestion('Write a business plan', Icons.edit_note_rounded),
        suggestion('Explain a hard topic', Icons.lightbulb_outline_rounded),
        suggestion('Help me code', Icons.code_rounded),
        suggestion('Research an idea', Icons.travel_explore_rounded),
      ]),
    ],
  )));

  Widget suggestion(String text, IconData icon) => ActionChip(
    avatar: Icon(icon, size: 17, color: accent), label: Text(text), backgroundColor: panel,
    side: BorderSide(color: Colors.white.withValues(alpha: 0.07)),
    onPressed: () { chatController.text = text; chatController.selection = TextSelection.collapsed(offset: text.length); });

  Widget createPage() => ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 28), children: [
    const Text('Creation Studio', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w800)),
    const SizedBox(height: 7),
    const Text('Create images, videos, and music from a native app interface.', style: TextStyle(color: muted, height: 1.45)),
    const SizedBox(height: 22),
    Row(children: [
      creationChoice('image', Icons.image_outlined, 'Image'),
      const SizedBox(width: 9), creationChoice('video', Icons.movie_creation_outlined, 'Video'),
      const SizedBox(width: 9), creationChoice('music', Icons.music_note_rounded, 'Music'),
    ]),
    const SizedBox(height: 18),
    TextField(controller: promptController, minLines: 4, maxLines: 8,
      decoration: InputDecoration(alignLabelWithHint: true, contentPadding: const EdgeInsets.all(17),
        hintText: creation == 'image' ? 'Describe the image you want to generate…'
          : creation == 'video' ? 'Describe the video scene, movement, and style…'
          : 'Describe the genre, mood, instruments, and style…')),
    const SizedBox(height: 13),
    SizedBox(height: 52, child: FilledButton.icon(onPressed: creating ? null : generate,
      icon: creating ? const SizedBox(width: 19, height: 19, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.auto_awesome_rounded),
      label: Text(creating ? 'Creating…' : 'Generate ' + creation[0].toUpperCase() + creation.substring(1)))),
    if (status.isNotEmpty) ...[
      const SizedBox(height: 16),
      Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: panel, borderRadius: BorderRadius.circular(16)),
        child: Row(children: [
          if (creating) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
          else const Icon(Icons.check_circle_outline_rounded, color: Color(0xFF55D6BE)),
          const SizedBox(width: 11), Expanded(child: Text(status, style: const TextStyle(color: muted))),
        ])),
    ],
    if (error != null && tab == 1) ...[const SizedBox(height: 12), errorBanner(error!, () => setState(() => error = null))],
    if (resultUrl != null) ...[
      const SizedBox(height: 18),
      Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: panel,
        borderRadius: BorderRadius.circular(20), border: Border.all(color: accent.withValues(alpha: 0.25))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Your creation is ready', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
          const SizedBox(height: 12),
          if (creation == 'image') ClipRRect(borderRadius: BorderRadius.circular(14),
            child: Image.network(resultUrl!, fit: BoxFit.contain,
              loadingBuilder: (_, child, progress) => progress == null ? child : const SizedBox(height: 180, child: Center(child: CircularProgressIndicator())),
              errorBuilder: (_, __, ___) => const Text('Preview unavailable. Open the result link below.'))),
          const SizedBox(height: 12),
          OutlinedButton.icon(onPressed: () => launchUrl(Uri.parse(resultUrl!), mode: LaunchMode.externalApplication),
            icon: const Icon(Icons.open_in_new_rounded),
            label: Text(creation == 'music' ? 'Listen / open audio' : creation == 'video' ? 'Open video' : 'Open image')),
        ])),
    ],
    const SizedBox(height: 16),
    Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: panel, borderRadius: BorderRadius.circular(16)),
      child: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(Icons.info_outline_rounded, color: accent), SizedBox(width: 10),
        Expanded(child: Text('Generation requires working Kie AI credentials and available provider credits. Generation time depends on the provider.', style: TextStyle(color: muted, height: 1.45))),
      ])),
  ]);

  Widget creationChoice(String value, IconData icon, String label) {
    final selected = creation == value;
    return Expanded(child: InkWell(borderRadius: BorderRadius.circular(17),
      onTap: creating ? null : () => setState(() { creation = value; status = ''; resultUrl = null; error = null; }),
      child: AnimatedContainer(duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 5),
        decoration: BoxDecoration(color: selected ? accent.withValues(alpha: 0.15) : panel,
          borderRadius: BorderRadius.circular(17), border: Border.all(color: selected ? accent : Colors.white.withValues(alpha: 0.06))),
        child: Column(children: [
          Icon(icon, color: selected ? accent : muted, size: 24), const SizedBox(height: 7),
          Text(label, style: TextStyle(fontWeight: FontWeight.w600, color: selected ? Colors.white : muted)),
        ]))));
  }

  Widget settingsPage() => ListView(padding: const EdgeInsets.all(18), children: [
    const Text('Settings & Status', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w800)),
    const SizedBox(height: 8),
    const Text('Native Flutter workspace connected to the ZIRRO API.', style: TextStyle(color: muted)),
    const SizedBox(height: 22),
    settingTile(Icons.smartphone_rounded, 'Native Flutter interface', 'No WebView; screens and controls are built with Flutter widgets.'),
    settingTile(Icons.forum_outlined, 'AI chat', 'OpenRouter through your ZIRRO server.'),
    settingTile(Icons.palette_outlined, 'Image generation', 'Kie AI image generation endpoint.'),
    settingTile(Icons.movie_outlined, 'Video generation', 'Kie AI video generation endpoint.'),
    settingTile(Icons.music_note_rounded, 'Music generation', 'Kie AI / Suno endpoint.'),
    settingTile(Icons.travel_explore_rounded, 'Web search', 'Optional Tavily integration; enable it in Assistant.'),
    const SizedBox(height: 16),
    FilledButton.icon(onPressed: checking ? null : checkHealth,
      icon: checking ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.health_and_safety_outlined),
      label: const Text('Check server connection')),
    const SizedBox(height: 12),
    const Text('API keys stay on the server. Configure provider credentials in Render or your configured Supabase proxy.', style: TextStyle(color: muted, height: 1.5)),
  ]);

  Widget settingTile(IconData icon, String title, String subtitle) => Container(
    margin: const EdgeInsets.only(bottom: 10), padding: const EdgeInsets.all(15),
    decoration: BoxDecoration(color: panel, borderRadius: BorderRadius.circular(17)),
    child: Row(children: [
      Container(width: 42, height: 42, decoration: BoxDecoration(color: accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(13)),
        child: Icon(icon, color: accent)),
      const SizedBox(width: 13),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 4), Text(subtitle, style: const TextStyle(color: muted, fontSize: 12, height: 1.4)),
      ])),
    ]));

  Future<void> checkHealth() async {
    if (checking) return;
    setState(() => checking = true);
    try {
      final data = await request('/api/health');
      if (!mounted) return;
      final chat = data['openrouter_configured'] == true ? 'OpenRouter configured' : 'OpenRouter key missing';
      final media = data['image_generation_configured'] == true ? 'Kie AI configured' : 'Kie AI needs setup';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Server online · ' + chat + ' · ' + media)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Connection check failed: ' + cleanError(e))));
    } finally {
      if (mounted) setState(() => checking = false);
    }
  }

  Widget errorBanner(String message, VoidCallback dismiss) => Container(
    margin: const EdgeInsets.fromLTRB(14, 6, 14, 6), padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: const Color(0xFF3B1C2A), borderRadius: BorderRadius.circular(14)),
    child: Row(children: [
      const Icon(Icons.error_outline_rounded, color: Color(0xFFFFA7B7)), const SizedBox(width: 9),
      Expanded(child: Text(message, style: const TextStyle(color: Color(0xFFFFDDE4), fontSize: 12))),
      IconButton(onPressed: dismiss, icon: const Icon(Icons.close_rounded, size: 18)),
    ]));
}

class Bubble extends StatelessWidget {
  const Bubble({super.key, required this.isUser, required this.text});
  final bool isUser;
  final String text;
  @override
  Widget build(BuildContext context) => Align(
    alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
    child: Container(constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.86),
      margin: const EdgeInsets.symmetric(vertical: 6), padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
      decoration: BoxDecoration(color: isUser ? const Color(0xFF302A58) : panel,
        borderRadius: BorderRadius.only(topLeft: const Radius.circular(18), topRight: const Radius.circular(18),
          bottomLeft: Radius.circular(isUser ? 18 : 5), bottomRight: Radius.circular(isUser ? 5 : 18)),
        border: Border.all(color: isUser ? accent.withValues(alpha: 0.25) : Colors.white.withValues(alpha: 0.05))),
      child: SelectableText(text, style: const TextStyle(fontSize: 14, height: 1.5))));
}
