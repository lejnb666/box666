package com.streammonitor.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.streammonitor.model.entity.UserInfo;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.Optional;

/**
 * 用户信息数据访问层
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Mapper
public interface UserInfoRepository extends BaseMapper<UserInfo> {

    /**
     * 根据OpenID查询用户信息
     *
     * @param openid 微信OpenID
     * @return 用户信息
     */
    @Select("SELECT * FROM user_info WHERE openid = #{openid} AND status = 1")
    Optional<UserInfo> findByOpenid(@Param("openid") String openid);

    /**
     * 根据OpenID更新用户信息
     *
     * @param userInfo 用户信息
     * @return 更新结果
     */
    int updateByOpenid(UserInfo userInfo);

    /**
     * 统计活跃用户数
     *
     * @return 活跃用户数
     */
    @Select("SELECT COUNT(*) FROM user_info WHERE status = 1")
    Long countActiveUsers();
}