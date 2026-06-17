package com.reshaqa.reshaqa

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.Context
import android.net.Uri
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetLaunchIntent
import es.antonborri.home_widget.HomeWidgetProvider

/// ودجت الشاشة الرئيسية: يعرض المتبقي من السعرات + فتح الإضافة السريعة.
class ReshaqaWidgetProvider : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: android.content.SharedPreferences
    ) {
        appWidgetIds.forEach { widgetId ->
            val views = RemoteViews(context.packageName, R.layout.reshaqa_widget).apply {
                val label = widgetData.getString("label", "افتح رشاقة") ?: "افتح رشاقة"
                val eaten = widgetData.getInt("eaten", 0)
                val target = widgetData.getInt("target", 0)
                setTextViewText(R.id.widget_label, label)
                setTextViewText(R.id.widget_sub, "$eaten / $target سعرة")

                val pendingIntent: PendingIntent = HomeWidgetLaunchIntent.getActivity(
                    context,
                    MainActivity::class.java,
                    Uri.parse("reshaqa://add")
                )
                setOnClickPendingIntent(R.id.widget_root, pendingIntent)
            }
            appWidgetManager.updateAppWidget(widgetId, views)
        }
    }
}
