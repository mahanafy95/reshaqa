import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';

/// المساعد الذكي 🤖 — محادثة حرّة متعددة الأدوار حول التغذية واللياقة
/// والوصفات والتحفيز. منفصل تماماً عن تسجيل الأكل.
class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key});

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  /// المحادثة في الذاكرة: كل عنصر {'role': 'user'|'assistant', 'content': str}.
  final List<Map<String, String>> _msgs = [];
  bool _sending = false;
  bool _loadingHistory = true;

  // أمثلة سريعة تظهر في الحالة الفارغة.
  static const _examples = [
    'اعملي نظام تخسيس',
    'اكل ايه قبل الجيم؟',
    'أكلت طبق كشري وسلطة — ضيفهم',
    'وصفة عشا خفيفة وصحية',
  ];

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  /// يستعيد المحادثة المحفوظة من السيرفر عند فتح الشاشة (تستمر بين الجلسات وعبر الأجهزة).
  Future<void> _loadHistory() async {
    try {
      final hist = await Api.assistantHistory();
      if (!mounted) return;
      setState(() {
        _msgs
          ..clear()
          ..addAll(hist.map((m) => {
                'role': (m['role'] ?? 'assistant').toString(),
                'content': (m['content'] ?? '').toString(),
              }));
        _loadingHistory = false;
      });
      _scrollToEnd();
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadingHistory = false); // نبدأ فاضي لو فشل التحميل
    }
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      }
    });
  }

  // تاريخ اليوم المحلي (YYYY-MM-DD) — يُمرَّر عشان تسجيل الوجبة يكون في اليوم الصح.
  String _todayIso() {
    final n = DateTime.now();
    final mm = n.month.toString().padLeft(2, '0');
    final dd = n.day.toString().padLeft(2, '0');
    return '${n.year}-$mm-$dd';
  }

  // نوع وجبة افتراضي حسب الوقت لو الـ AI ماحددش (الفطار/الغدا/العشا/سناك).
  String _mealForNow() {
    final h = DateTime.now().hour;
    if (h < 11) return 'breakfast';
    if (h < 16) return 'lunch';
    if (h < 21) return 'dinner';
    return 'snack';
  }

  Future<void> _clearChat() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('مسح المحادثة؟'),
        content: const Text('هتتمسح كل الرسائل مع المساعد. مش هيأثّر على أكلك المسجّل.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('مسح')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await Api.clearAssistantHistory();
      if (!mounted) return;
      setState(() => _msgs.clear());
    } catch (e) {
      if (!mounted) return;
      showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _input.text).trim();
    if (text.isEmpty || _sending) return;
    _input.clear();
    setState(() {
      _msgs.add({'role': 'user', 'content': text});
      _sending = true;
    });
    _scrollToEnd();

    // نرسل آخر ~10 أدوار فقط (مع الرسالة الجديدة) — كفاية للسياق وتسجيل الوجبة.
    final recent = _msgs.length > 10 ? _msgs.sublist(_msgs.length - 10) : List<Map<String, String>>.from(_msgs);
    try {
      final res = await Api.assistantChat(recent, date: _todayIso(), defaultMeal: _mealForNow());
      if (!mounted) return;
      final reply = (res['reply'] ?? '').toString();
      final logged = res['logged'] == true;
      setState(() {
        _msgs.add({'role': 'assistant', 'content': reply});
        _sending = false;
      });
      _scrollToEnd();
      if (logged) {
        final cals = (res['logged_total_calories'] ?? 0);
        showSnack(context, 'اتسجّلت في يومك ✅ (~${(cals as num).round()} سعرة)');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('المساعد الذكي 🤖'),
        actions: [
          if (_msgs.isNotEmpty)
            IconButton(
              tooltip: 'مسح المحادثة',
              icon: const Icon(Icons.delete_outline),
              onPressed: _sending ? null : _clearChat,
            ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _loadingHistory
                ? const Center(child: CircularProgressIndicator(color: AppColors.teal))
                : _msgs.isEmpty
                ? _EmptyState(examples: _examples, onPick: _send)
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: _msgs.length + (_sending ? 1 : 0),
                    itemBuilder: (_, i) {
                      if (i >= _msgs.length) return const _TypingBubble();
                      return _bubble(_msgs[i]);
                    },
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
                      minLines: 1,
                      maxLines: 4,
                      onSubmitted: (_) => _send(),
                      decoration: const InputDecoration(
                        hintText: 'اسأل المساعد الذكي…',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton.filled(
                    onPressed: _sending ? null : () => _send(),
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

  Widget _bubble(Map<String, String> m) {
    final mine = m['role'] == 'user';
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
        decoration: BoxDecoration(
          color: mine ? AppColors.teal : Colors.grey.shade200,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(
          m['content'] ?? '',
          style: TextStyle(color: mine ? Colors.white : AppColors.textDark),
        ),
      ),
    );
  }
}

/// فقاعة "بيكتب…" أثناء انتظار رد المساعد.
class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: BorderRadius.circular(14),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.teal),
            ),
            SizedBox(width: 10),
            Text('بيكتب…', style: TextStyle(color: AppColors.textMuted)),
          ],
        ),
      ),
    );
  }
}

/// حالة فارغة ترحيبية مع أمثلة سريعة (chips) تملأ وتُرسل الإدخال.
class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.examples, required this.onPick});
  final List<String> examples;
  final void Function(String) onPick;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 24),
          CircleAvatar(
            radius: 40,
            backgroundColor: AppColors.teal.withValues(alpha: 0.12),
            child: const Text('🤖', style: TextStyle(fontSize: 40)),
          ),
          const SizedBox(height: 16),
          const Text(
            'أهلاً! أنا مساعدك الذكي',
            style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'اسألني عن التغذية، اللياقة، الوصفات، أو أي حاجة تحفّزك على هدفك 💚\n'
            'وتقدر كمان تقولي «ضيف اللي أكلته» وأنا أسجّله في يومك.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textMuted),
          ),
          const SizedBox(height: 24),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final ex in examples)
                ActionChip(
                  label: Text(ex),
                  backgroundColor: AppColors.teal.withValues(alpha: 0.1),
                  side: BorderSide(color: AppColors.teal.withValues(alpha: 0.3)),
                  onPressed: () => onPick(ex),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
