import { Capacitor } from '@capacitor/core'
import { PushNotifications } from '@capacitor/push-notifications'
import { registerPushDevice } from './api'

export async function setupPushNotifications() {
  if (!Capacitor.isNativePlatform()) return () => {}
  let registration
  const registrationListener = await PushNotifications.addListener('registration', (token) => {
    registration = token.value
    registerPushDevice(token.value, Capacitor.getPlatform()).catch(() => {})
  })
  const actionListener = await PushNotifications.addListener('registrationError', () => {})
  const receivedListener = await PushNotifications.addListener('pushNotificationReceived', () => {})
  const actionReceivedListener = await PushNotifications.addListener('pushNotificationActionPerformed', () => {})
  const permission = await PushNotifications.checkPermissions()
  const granted = permission.receive === 'granted' ? permission : await PushNotifications.requestPermissions()
  if (granted.receive === 'granted') await PushNotifications.register()
  return async () => {
    if (registration) {
      // Device tokens remain valid across app restarts; unregister is handled server-side when replaced.
    }
    await Promise.all([registrationListener.remove(), actionListener.remove(), receivedListener.remove(), actionReceivedListener.remove()])
  }
}