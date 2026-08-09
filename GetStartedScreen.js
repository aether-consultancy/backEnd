import { useState, useCallback, useRef, useEffect } from 'react';
import { View, Text, TouchableOpacity, Animated, Easing, Dimensions, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { getKidAccounts } from '../../utils/kidAccounts';
import { getAnimalEmoji } from '../../utils/kidProfileOptions';
import styles from './GetStartedScreen.styles';

const { width: W } = Dimensions.get('window');

const PURPLE = '#6D28D9';
const CORAL = '#FF6B5B';
const NAVY = '#111827';
const WHITE = '#FFFFFF';

function Fade({ children, delay = 0, style }) {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(anim, {
      toValue: 1,
      duration: 420,
      delay,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, []);
  return (
    <Animated.View
      style={[
        style,
        {
          opacity: anim,
          transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [16, 0] }) }],
        },
      ]}
    >
      {children}
    </Animated.View>
  );
}

function ProfileRow({ account, index, onPress }) {
  const emoji = getAnimalEmoji(account.favoriteAnimal);
  const initial = (account.fullName || '?').trim().charAt(0).toUpperCase();
  return (
    <Fade delay={index * 70} style={styles.profileRow}>
      <TouchableOpacity activeOpacity={0.7} style={styles.profileTouch} onPress={onPress}>
        <View style={styles.profileIconBox}>
          {emoji ? <Text style={styles.profileEmoji}>{emoji}</Text> : <Text style={styles.profileInitial}>{initial}</Text>}
        </View>
        <Text style={styles.profileName}>{(account.fullName || '').split(' ')[0]}</Text>
        <Ionicons name="chevron-forward" size={18} color={NAVY} style={{ opacity: 0.35 }} />
      </TouchableOpacity>
    </Fade>
  );
}

export default function GetStartedScreen({ navigation }) {
  const [accounts, setAccounts] = useState([]);

  useFocusEffect(
    useCallback(() => {
      getKidAccounts().then(setAccounts);
    }, [])
  );

  if (accounts.length > 0) {
    return (
      <View style={styles.screen}>
        <View style={styles.listHeader}>
          <Text style={styles.listKicker}>EDUWAY</Text>
          <Text style={styles.listTitle}>Pick your profile</Text>
        </View>
        <ScrollView contentContainerStyle={styles.listWrap}>
          {accounts.map((a, i) => (
            <ProfileRow
              key={a.kidId}
              account={a}
              index={i}
              onPress={() => navigation.navigate('KidLogin', { kidId: a.kidId, fullName: a.fullName })}
            />
          ))}
          <TouchableOpacity style={styles.addRow} activeOpacity={0.7} onPress={() => navigation.navigate('ScanQr')}>
            <View style={styles.addIconBox}>
              <Ionicons name="add" size={20} color={PURPLE} />
            </View>
            <Text style={styles.addRowText}>Add a new profile</Text>
          </TouchableOpacity>
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <LinearGradient colors={[PURPLE, CORAL]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.heroCard}>
        <Fade style={styles.heroTop}>
          <Text style={styles.wordmark}>eduway</Text>
        </Fade>
        <Fade delay={100}>
          <Text style={styles.heroHeadline}>Learning{'\n'}starts here.</Text>
          <Text style={styles.heroSub}>Scan the code your parent shows you and jump in.</Text>
        </Fade>
      </LinearGradient>

      <View style={styles.bottomPanel}>
        <Fade delay={180} style={styles.scanCard}>
          <TouchableOpacity activeOpacity={0.85} style={styles.scanTouch} onPress={() => navigation.navigate('ScanQr')}>
            <View style={styles.scanIconBox}>
              <Ionicons name="qr-code-outline" size={26} color={WHITE} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.scanTitle}>Scan QR Code</Text>
              <Text style={styles.scanSub}>Open with eduParent app</Text>
            </View>
            <Ionicons name="arrow-forward-circle" size={30} color={PURPLE} />
          </TouchableOpacity>
        </Fade>
      </View>
    </View>
  );
}
