import 'package:flutter/material.dart';

import '../core/theme.dart';

/// شريط تقدّم ماكرو (اسم + متاكل/هدف + لون حالة).
class MacroBar extends StatelessWidget {
  const MacroBar({super.key, required this.name, required this.eaten, required this.target, required this.color});
  final String name;
  final double eaten;
  final double target;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final ratio = target <= 0 ? 0.0 : (eaten / target).clamp(0.0, 1.5);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
              Text('${eaten.round()} / ${target.round()} جم', style: TextStyle(color: mutedColor(context))),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: ratio > 1 ? 1 : ratio,
              minHeight: 9,
              backgroundColor: color.withValues(alpha: 0.15),
              valueColor: AlwaysStoppedAnimation(color),
            ),
          ),
        ],
      ),
    );
  }
}

/// بطاقة قسم بعنوان.
class SectionCard extends StatelessWidget {
  const SectionCard({super.key, required this.child, this.title, this.padding});
  final Widget child;
  final String? title;
  final EdgeInsets? padding;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: padding ?? const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (title != null) ...[
              Text(title!, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
            ],
            child,
          ],
        ),
      ),
    );
  }
}

/// زر إجراء سريع في الشبكة.
class QuickAction extends StatelessWidget {
  const QuickAction({super.key, required this.icon, required this.label, required this.onTap, this.color = AppColors.teal});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: surfaceColor(context),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 6, offset: const Offset(0, 2))],
        ),
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircleAvatar(radius: 24, backgroundColor: color.withValues(alpha: 0.12), child: Icon(icon, color: color)),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

void showSnack(BuildContext context, String msg, {bool error = false}) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
    content: Text(msg),
    backgroundColor: error ? AppColors.danger : AppColors.teal,
  ));
}
