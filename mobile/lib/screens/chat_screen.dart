import 'dart:async';

import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';

/// محادثة مع صديق — رسائل + تشجيع، مع تحديث دوري (polling) كل 4 ثواني.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.friendId, required this.friendName});
  final int friendId;
  final String friendName;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<Map<String, dynamic>> _msgs = [];
  int _lastId = 0;
  bool _loading = true;
  bool _sending = false;
  bool _fetching = false;   // قفل يمنع تداخل طلبين على نفس الوقت
  int _failures = 0;        // لعمل backoff عند تكرار الفشل (شبكة واقعة)
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _fetch(initial: true);
    _scheduleNext();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  /// مؤقّت يعيد جدولة نفسه بعد كل جلب (مش Timer.periodic) — يستنّى الطلب يخلّص الأول،
  /// ويباعد بين المحاولات لو الشبكة بتفشل عشان منستنزفش البطارية والداتا.
  void _scheduleNext() {
    final secs = _failures >= 3 ? 20 : (_failures >= 1 ? 8 : 4);
    _poll = Timer(Duration(seconds: secs), () async {
      await _fetch();
      if (mounted) _scheduleNext();
    });
  }

  Future<void> _fetch({bool initial = false}) async {
    if (_fetching) return;  // طلب لسه شغّال — منعملش تاني
    _fetching = true;
    try {
      final list = await Api.messages(widget.friendId, afterId: _lastId);
      _failures = 0;
      if (list.isEmpty) {
        if (initial && mounted) setState(() => _loading = false);
        return;
      }
      if (!mounted) return;
      setState(() {
        for (final m in list) {
          _msgs.add(Map<String, dynamic>.from(m));
          _lastId = (m['id'] as num).toInt();
        }
        _loading = false;
      });
      _scrollToEnd();
    } catch (_) {
      _failures++;
      if (initial && mounted) setState(() => _loading = false);
    } finally {
      _fetching = false;
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    _input.clear();
    try {
      final m = await Api.sendMessage(widget.friendId, text);
      if (!mounted) return;
      setState(() {
        _msgs.add(Map<String, dynamic>.from(m));
        _lastId = (m['id'] as num).toInt();
      });
      _scrollToEnd();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _cheer() async {
    try {
      final m = await Api.cheer(widget.friendId);
      if (!mounted) return;
      setState(() {
        _msgs.add(Map<String, dynamic>.from(m));
        _lastId = (m['id'] as num).toInt();
      });
      _scrollToEnd();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.friendName),
        actions: [
          IconButton(
            tooltip: 'شجّعه',
            onPressed: _cheer,
            icon: const Text('💪', style: TextStyle(fontSize: 20)),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _msgs.isEmpty
                    ? Center(
                        child: Text('ابدأ المحادثة وشجّع صاحبك 💚',
                            style: TextStyle(color: mutedColor(context))))
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.all(12),
                        itemCount: _msgs.length,
                        itemBuilder: (_, i) => _bubble(_msgs[i]),
                      ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(),
                      decoration: const InputDecoration(
                        hintText: 'اكتب رسالة…',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton.filled(
                    onPressed: _sending ? null : _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bubble(Map<String, dynamic> m) {
    final mine = m['mine'] == true;
    final cheer = m['kind'] == 'cheer';
    return Align(
      alignment: mine ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.72),
        decoration: BoxDecoration(
          color: cheer
              ? AppColors.orange.withValues(alpha: 0.15)
              : (mine ? AppColors.teal : surfaceColor(context)),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(
          m['body']?.toString() ?? '',
          style: TextStyle(
            color: cheer
                ? Theme.of(context).colorScheme.onSurface
                : (mine ? Colors.white : Theme.of(context).colorScheme.onSurface),
            fontWeight: cheer ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }
}
