// lib/models/user.dart

/// User model representing authenticated user
/// Matches backend users table schema
class User {
  final String id;
  final String email;
  final String? fullName;
  final DateTime createdAt;
  final bool isActive;
  final String kycStatus; // 'pending', 'approved', 'rejected'
  final String? profileImageUrl;
  final Map<String, dynamic>? preferences;

  User({
    required this.id,
    required this.email,
    this.fullName,
    required this.createdAt,
    this.isActive = true,
    this.kycStatus = 'pending',
    this.profileImageUrl,
    this.preferences,
  });

  /// Create User from backend JSON response
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? json['fullName']?.toString(),
      createdAt: _parseDateTime(json['created_at'] ?? json['createdAt']),
      isActive: json['is_active'] ?? json['isActive'] ?? true,
      kycStatus: json['kyc_status']?.toString() ??
          json['kycStatus']?.toString() ??
          'pending',
      profileImageUrl: json['profile_image_url']?.toString() ??
          json['profileImageUrl']?.toString(),
      preferences: json['preferences'] as Map<String, dynamic>?,
    );
  }

  /// Convert User to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      if (fullName != null) 'full_name': fullName,
      'created_at': createdAt.toIso8601String(),
      'is_active': isActive,
      'kyc_status': kycStatus,
      if (profileImageUrl != null) 'profile_image_url': profileImageUrl,
      if (preferences != null) 'preferences': preferences,
    };
  }

  /// Check if user is KYC verified
  bool get isKycVerified => kycStatus == 'approved';

  /// Check if user is KYC pending
  bool get isKycPending => kycStatus == 'pending';

  /// Check if user is KYC rejected
  bool get isKycRejected => kycStatus == 'rejected';

  /// Get display name (full name or email)
  String get displayName => fullName ?? email.split('@').first;

  /// Get initials for avatar
  String get initials {
    if (fullName != null && fullName!.isNotEmpty) {
      final parts = fullName!.split(' ');
      if (parts.length >= 2) {
        return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
      }
      return fullName![0].toUpperCase();
    }
    return email[0].toUpperCase();
  }

  Null get balance => null;

  Null get isVerified => null;

  Null get preferredCurrency => null;

  /// Copy with method
  User copyWith({
    String? id,
    String? email,
    String? fullName,
    DateTime? createdAt,
    bool? isActive,
    String? kycStatus,
    String? profileImageUrl,
    Map<String, dynamic>? preferences,
  }) {
    return User(
      id: id ?? this.id,
      email: email ?? this.email,
      fullName: fullName ?? this.fullName,
      createdAt: createdAt ?? this.createdAt,
      isActive: isActive ?? this.isActive,
      kycStatus: kycStatus ?? this.kycStatus,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      preferences: preferences ?? this.preferences,
    );
  }

  /// Helper to parse DateTime
  static DateTime _parseDateTime(dynamic value) {
    if (value == null) return DateTime.now();
    if (value is DateTime) return value;
    if (value is String) return DateTime.tryParse(value) ?? DateTime.now();
    return DateTime.now();
  }
}
