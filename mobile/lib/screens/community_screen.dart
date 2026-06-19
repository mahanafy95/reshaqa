import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';
import 'chat_screen.dart';

/// شاشة المجتمع — الأصدقاء، الطلبات، والبحث عن أشخاص لإضافتهم.
class CommunityScreen extends StatefulWidget {
  const CommunityScreen({super.key});
  @override
  State<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends State<CommunityScreen> {
  Map<String, dynamic> _data = {'friends': [], 'incoming': [], 'outgoing': []};
  bool _loading = true;
  final _search = TextEditingController();
  List<dynamic> _results = [];
  bool _searching = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      _data = await Api.friends();
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _doSearch() async {
    final q = _search.text.trim();
    if (q.isEmpty) return;
    setState(() => _searching = true);
    try {
      _results = await Api.searchUsers(q);
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  Future<void> _act(Future<dynamic> Function() fn) async {
    try {
      await fn();
      await _load();
      if (_search.text.trim().isNotEmpty) await _doSearch();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  void _openChat(int id, String name) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => ChatScreen(friendId: id, friendName: name)))
        .then((_) => _load());
  }

  @override
  Widget build(BuildContext context) {
    final friends = (_data['friends'] as List?) ?? [];
    final incoming = (_data['incoming'] as List?) ?? [];
    final outgoing = (_data['outgoing'] as List?) ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('المجتمع 👥')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // البحث والإضافة
                  Row(children: [
                    Expanded(
                      child: TextField(
                        controller: _search,
                        textInputAction: TextInputAction.search,
                        onSubmitted: (_) => _doSearch(),
                        decoration: const InputDecoration(
                          hintText: 'دوّر على صاحبك باسمه…',
                          prefixIcon: Icon(Icons.search),
                          border: OutlineInputBorder(),
                          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    ElevatedButton(onPressed: _searching ? null : _doSearch, child: const Text('بحث')),
                  ]),
                  if (_results.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    SectionCard(
                      title: 'نتائج البحث',
                      child: Column(children: _results.map((u) => _searchRow(u)).toList()),
                    ),
                  ],
                  const SizedBox(height: 12),

                  if (incoming.isNotEmpty)
                    SectionCard(
                      title: 'طلبات صداقة (${incoming.length})',
                      child: Column(children: incoming.map((f) => _requestRow(f)).toList()),
                    ),
                  if (incoming.isNotEmpty) const SizedBox(height: 12),

                  SectionCard(
                    title: 'أصدقائي (${friends.length})',
                    child: friends.isEmpty
                        ? Padding(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            child: Text('لسه مفيش أصدقاء — دوّر وأضف صحابك يشجّعوك 💚',
                                style: TextStyle(color: mutedColor(context))))
                        : Column(children: friends.map((f) => _friendRow(f)).toList()),
                  ),

                  if (outgoing.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    SectionCard(
                      title: 'طلبات مُرسَلة (${outgoing.length})',
                      child: Column(
                        children: outgoing
                            .map((f) => ListTile(
                                  contentPadding: EdgeInsets.zero,
                                  dense: true,
                                  title: Text(f['username'] ?? ''),
                                  trailing: Text('في الانتظار…',
                                      style: TextStyle(color: mutedColor(context), fontSize: 12)),
                                ))
                            .toList(),
                      ),
                    ),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _friendRow(dynamic f) {
    final unread = (f['unread'] as num?)?.toInt() ?? 0;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        backgroundColor: AppColors.teal.withValues(alpha: 0.15),
        child: Text((f['username'] ?? '?').toString().characters.first),
      ),
      title: Text(f['username'] ?? ''),
      trailing: unread > 0
          ? CircleAvatar(radius: 11, backgroundColor: AppColors.orange,
              child: Text('$unread', style: const TextStyle(color: Colors.white, fontSize: 12)))
          : Icon(Icons.chevron_left, color: mutedColor(context)),
      onTap: () => _openChat((f['user_id'] as num).toInt(), f['username'] ?? ''),
      onLongPress: () => _confirmRemove((f['user_id'] as num).toInt(), f['username'] ?? ''),
    );
  }

  Widget _requestRow(dynamic f) {
    final id = (f['user_id'] as num).toInt();
    return ListTile(
      contentPadding: EdgeInsets.zero,
      dense: true,
      title: Text(f['username'] ?? ''),
      trailing: Row(mainAxisSize: MainAxisSize.min, children: [
        TextButton(onPressed: () => _act(() => Api.acceptFriend(id)), child: const Text('قبول')),
        TextButton(
          onPressed: () => _act(() => Api.removeFriend(id)),
          style: TextButton.styleFrom(foregroundColor: AppColors.danger),
          child: const Text('رفض'),
        ),
      ]),
    );
  }

  Widget _searchRow(dynamic u) {
    final id = (u['id'] as num).toInt();
    final rel = u['relation'];
    Widget trailing;
    if (rel == 'friend') {
      trailing = const Text('صديق ✓', style: TextStyle(color: AppColors.teal, fontSize: 13));
    } else if (rel == 'pending_out') {
      trailing = Text('مُرسَل…', style: TextStyle(color: mutedColor(context), fontSize: 12));
    } else if (rel == 'pending_in') {
      trailing = TextButton(onPressed: () => _act(() => Api.acceptFriend(id)), child: const Text('قبول'));
    } else {
      trailing = TextButton.icon(
        onPressed: () => _act(() => Api.friendRequest(id)),
        icon: const Icon(Icons.person_add_alt, size: 18),
        label: const Text('إضافة'),
      );
    }
    return ListTile(
      contentPadding: EdgeInsets.zero,
      dense: true,
      title: Text(u['username'] ?? ''),
      trailing: trailing,
    );
  }

  Future<void> _confirmRemove(int id, String name) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('إزالة صديق'),
        content: Text('تحب تشيل "$name" من أصدقائك؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('إزالة'),
          ),
        ],
      ),
    );
    if (ok == true) await _act(() => Api.removeFriend(id));
  }
}
